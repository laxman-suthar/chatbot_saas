import os
from celery import shared_task
from django.utils import timezone
from .models import Document
from .rag import ingest_document, delete_document_chunks


@shared_task(bind=True, max_retries=3)
def process_document(self, doc_id: str):
    """
    Celery task to process uploaded document
    Loads, chunks, embeds and stores in ChromaDB
    """
    try:
        doc = Document.objects.get(id=doc_id)

        # mark as processing
        doc.status = 'processing'
        doc.save()

        # get file details
        file_path = doc.file.path
        file_type = doc.file_type

        # ingest into ChromaDB
        chunk_count = ingest_document(
            website_id=str(doc.website.id),
            file_path=file_path,
            file_type=file_type,
            doc_id=str(doc.id)
        )

        # mark as processed
        doc.status = 'processed'
        doc.chunk_count = chunk_count
        doc.processed_at = timezone.now()
        doc.save()

    except Document.DoesNotExist:
        pass

    except Exception as exc:
        doc = Document.objects.get(id=doc_id)
        doc.status = 'failed'
        doc.error_message = str(exc)
        doc.save()
        # retry after 60 seconds
        raise self.retry(exc=exc, countdown=60)


@shared_task
def delete_document_task(website_id: str, doc_id: str):
    """
    Celery task to delete document chunks from ChromaDB
    """
    try:
        delete_document_chunks(
            website_id=website_id,
            doc_id=doc_id
        )
    except Exception as e:
        print(f"Error deleting chunks: {e}")