from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
import uuid
from websites.models import Website
from .models import Document
from .serializers import DocumentSerializer, DocumentUploadSerializer
from .kafka_producer import produce_document_upload, produce_document_delete


class DocumentListUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def get_website(self, website_id, user):
        try:
            return Website.objects.get(id=website_id, owner=user)
        except Website.DoesNotExist:
            return None

    @extend_schema(
        tags=['Knowledge Base'],
        summary='List all documents for a website',
        responses={200: DocumentSerializer(many=True)}
    )
    def get(self, request, website_id):
        website = self.get_website(website_id, request.user)
        if not website:
            return Response(
                {'error': 'Website not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        documents = Document.objects.filter(website=website)
        return Response(DocumentSerializer(documents, many=True).data)

    @extend_schema(
        tags=['Knowledge Base'],
        summary='Upload a document or paste text for RAG processing',
        description='''
        Two upload methods:

        1. **File Upload** (multipart/form-data): PDF, TXT, DOCX — max 10MB
        2. **Text Paste** (application/json): send { title, content, doc_type: "text" }

        Returns 202 Accepted. Document is queued for async processing via Kafka.
        ''',
        responses={202: DocumentSerializer},
    )

    def post(self, request, website_id):
        website = self.get_website(website_id, request.user)
        if not website:
            return Response(
                {'error': 'Website not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # ── File upload ───────────────────────────────────────────────────────
        if 'file' in request.FILES:
            serializer = DocumentUploadSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            file = request.FILES['file']
            ext = file.name.split('.')[-1]
            file.name= f'{uuid.uuid4()}.{ext}'
            doc = serializer.save(
                website=website,
                file_type=file.content_type,
                file_size=file.size,
                doc_type='file',
            )
            

            try:
                # ✅ Generate filename: {doc_id}.{extension}
                file_ext = file.name.split('.')[-1]  # Get extension from original filename
                filename = f"{doc.id}.{file_ext}"
                
                produce_document_upload(
                    doc_id=str(doc.id),
                    website_id=str(website.id),
                    file_path=doc.file.path,
                    doc_type='file',
                    title=doc.title,
                    filename=filename,  # ✅ Pass filename
                )
            except Exception as e:
                doc.status = 'failed'
                doc.error_message = f'Failed to queue: {str(e)}'
                doc.save()
                return Response(
                    {'error': 'Failed to queue document for processing'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(DocumentSerializer(doc).data, status=status.HTTP_202_ACCEPTED)

        # ── Text paste ────────────────────────────────────────────────────────
        elif request.data.get('doc_type') == 'text':
            text_content = request.data.get('content', '').strip()
            title = request.data.get('title', 'Untitled Document')

            if not text_content:
                return Response(
                    {'error': 'Content cannot be empty'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            doc = Document.objects.create(
                website=website,
                title=title,
                doc_type='text',
                text_content=text_content,
                status='pending',
            )

            try:
                # ✅ Generate filename: {doc_id}.text
                filename = f"{doc.id}.text"
                
                produce_document_upload(
                    doc_id=str(doc.id),
                    website_id=str(website.id),
                    text_content=text_content,
                    doc_type='text',
                    title=title,
                    filename=filename,  # ✅ Pass filename
                )
            except Exception as e:
                doc.status = 'failed'
                doc.error_message = f'Failed to queue: {str(e)}'
                doc.save()
                return Response(
                    {'error': 'Failed to queue document for processing'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(DocumentSerializer(doc).data, status=status.HTTP_202_ACCEPTED)
        return Response(
            {
                'error': 'Either file upload or text paste required',
                'help': 'Send file in multipart/form-data OR JSON with content + doc_type="text"',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class DocumentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_document(self, doc_id, user):
        try:
            return Document.objects.get(id=doc_id, website__owner=user)
        except Document.DoesNotExist:
            return None

    @extend_schema(
        tags=['Knowledge Base'],
        summary='Get document details',
        responses={200: DocumentSerializer}
    )
    def get(self, request, website_id, doc_id):
        doc = self.get_document(doc_id, request.user)
        if not doc:
            return Response({'error': 'Document not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(DocumentSerializer(doc).data)

    @extend_schema(
        tags=['Knowledge Base'],
        summary='Delete a document',
        responses={204: None}
    )
    def delete(self, request, website_id, doc_id):
        doc = self.get_document(doc_id, request.user)
        if not doc:
            return Response({'error': 'Document not found'}, status=status.HTTP_404_NOT_FOUND)

        # Produce delete event to Kafka so consumer cleans up ChromaDB chunks
        try:
            produce_document_delete(
                doc_id=str(doc.id),
                website_id=str(doc.website.id),
            )
        except Exception as e:
            # Log but don't block the delete
            print(f"Warning: Could not produce delete event: {e}")

        if doc.doc_type == 'file' and doc.file:
            doc.file.delete(save=False)
        doc.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class ReprocessDocumentView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Knowledge Base'],
        summary='Reprocess a failed document',
        responses={202: DocumentSerializer}
    )
    def post(self, request, website_id, doc_id):
        try:
            doc = Document.objects.get(id=doc_id, website__owner=request.user)
        except Document.DoesNotExist:
            return Response({'error': 'Document not found'}, status=status.HTTP_404_NOT_FOUND)

        if doc.status not in ['failed', 'pending']:
            return Response(
                {'error': 'Only failed or pending documents can be reprocessed'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        doc.status = 'pending'
        doc.error_message = ''
        doc.save()

        try:
            if doc.doc_type == 'file':
                produce_document_upload(
                    doc_id=str(doc.id),
                    website_id=str(doc.website.id),
                    file_path=doc.file.path,
                    doc_type='file',
                    title=doc.title,
                )
            else:
                produce_document_upload(
                    doc_id=str(doc.id),
                    website_id=str(doc.website.id),
                    text_content=doc.text_content,
                    doc_type='text',
                    title=doc.title,
                )
        except Exception as e:
            doc.status = 'failed'
            doc.error_message = f'Failed to queue: {str(e)}'
            doc.save()
            return Response({'error': 'Failed to requeue document'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(DocumentSerializer(doc).data, status=status.HTTP_202_ACCEPTED)