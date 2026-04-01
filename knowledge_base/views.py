from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiExample
from django.shortcuts import get_object_or_404

from websites.models import Website
from .models import Document
from .serializers import DocumentSerializer, DocumentUploadSerializer
from .tasks import process_document, delete_document_task


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
        return Response(
            DocumentSerializer(documents, many=True).data
        )

    @extend_schema(
        tags=['Knowledge Base'],
        summary='Upload a document for RAG processing',
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'title': {'type': 'string'},
                    'file': {'type': 'string', 'format': 'binary'}
                },
                'required': ['title', 'file']
            }
        },
        responses={202: DocumentSerializer},
    )
    def post(self, request, website_id):
        website = self.get_website(website_id, request.user)
        if not website:
            return Response(
                {'error': 'Website not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DocumentUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = request.FILES['file']
            doc = serializer.save(
                website=website,
                file_type=file.content_type,
                file_size=file.size
            )
            # trigger async processing
            process_document.delay(str(doc.id))

            return Response(
                DocumentSerializer(doc).data,
                status=status.HTTP_202_ACCEPTED
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class DocumentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_document(self, doc_id, user):
        try:
            return Document.objects.get(
                id=doc_id,
                website__owner=user
            )
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
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(DocumentSerializer(doc).data)

    @extend_schema(
        tags=['Knowledge Base'],
        summary='Delete a document',
        responses={204: None}
    )
    def delete(self, request, website_id, doc_id):
        doc = self.get_document(doc_id, request.user)
        if not doc:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        # delete chunks from ChromaDB async
        delete_document_task.delay(
            str(doc.website.id),
            str(doc.id)
        )
        # delete file and record
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
            doc = Document.objects.get(
                id=doc_id,
                website__owner=request.user
            )
            if doc.status not in ['failed', 'pending']:
                return Response(
                    {'error': 'Only failed or pending documents can be reprocessed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            doc.status = 'pending'
            doc.error_message = ''
            doc.save()
            process_document.delay(str(doc.id))
            return Response(
                DocumentSerializer(doc).data,
                status=status.HTTP_202_ACCEPTED
            )
        except Document.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )