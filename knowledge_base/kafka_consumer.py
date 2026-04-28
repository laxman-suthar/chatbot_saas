"""
Kafka Consumer for document processing.
Replaces Celery — consumes document-upload events and processes
them directly (chunking + embeddings + ChromaDB storage).

Run via: python knowledge_base/kafka_consumer.py
(Started as a separate Docker service)
"""

import os
import sys
import json
import logging
import django
import time
from django.utils.html import escape  
from datetime import datetime
import uuid
os.environ["ANONYMIZED_TELEMETRY"] = "False"
# ── Bootstrap Django before any app imports ──────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot.settings')
django.setup()
# ─────────────────────────────────────────────────────────────────────────────

from confluent_kafka import Consumer, KafkaException, KafkaError
from django.utils import timezone
from knowledge_base.models import Document
from knowledge_base.rag import ingest_document, ingest_text, delete_document_chunks
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)


def get_consumer() -> Consumer:
    return Consumer({
        'bootstrap.servers': os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'),
        'group.id': os.environ.get('KAFKA_CONSUMER_GROUP', 'doc-processors'),
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False,
        'max.poll.interval.ms': 600000,
        'session.timeout.ms': 30000,
    })


def generate_pdf_from_text(text_content: str, filename: str=None) -> str:
    """
    Generate a PDF from text content.
    Returns the file path.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        
        # Create media directory structure: media/documents/YYYY/MM/DD/
        today = datetime.now()
        media_dir = f"media/documents/{today.year}/{today.month:02d}/{today.day:02d}"
        os.makedirs(media_dir, exist_ok=True)
        
        # Convert .text to .pdf filename
        pdf_filename =  f"{uuid.uuid4()}.pdf"
        pdf_path = os.path.join(media_dir, pdf_filename)
        
        # Generate PDF
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Add title/heading
        story.append(Paragraph("Document Content", styles['Heading1']))
        story.append(Spacer(1, 0.2*inch))
        
        escaped_content = escape(text_content).replace('\n', '<br/>')
        # Add text content
        story.append(Paragraph(escaped_content, styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"✅ Generated PDF: {pdf_path}")
        logger.info(pdf_path)
        return pdf_path
        
    except Exception as e:
        logger.error(f"❌ Failed to generate PDF: {e}", exc_info=True)
        raise


def process_upload_event(data: dict):
    """Same as before, but now uses pgvector"""
    doc_id = data.get('doc_id')
    website_id = data.get('website_id')
    doc_type = data.get('doc_type', 'file')
    file_path = data.get('file_path')
    text_content = data.get('text_content')

    if not doc_id or not website_id:
        logger.error(f"❌ Missing doc_id or website_id")
        return

    try:
        doc = Document.objects.get(id=doc_id)
    except Document.DoesNotExist:
        logger.error(f"❌ Document {doc_id} not found")
        return

    doc.status = 'processing'
    doc.save(update_fields=['status'])

    try:
        if doc_type == 'file':
            chunk_count = ingest_document(
                website_id=website_id,
                file_path=file_path,
                file_type=doc.file_type,
                doc_id=doc_id,
            )
        elif doc_type == 'text':
            chunk_count = ingest_text(
                website_id=website_id,
                text_content=text_content,
                doc_id=doc_id,
            )

        doc.status = 'processed'
        doc.chunk_count = chunk_count
        doc.processed_at = timezone.now()
        doc.error_message = ''
        doc.save(update_fields=['status', 'chunk_count', 'processed_at', 'error_message'])
        logger.info(f"✅ Document {doc_id} processed — {chunk_count} chunks")

    except Exception as exc:
        logger.error(f"❌ Failed to process {doc_id}: {exc}", exc_info=True)
        doc.status = 'failed'
        doc.error_message = str(exc)
        doc.save(update_fields=['status', 'error_message'])


def process_delete_event(data: dict):
    """Delete document chunks from ChromaDB"""
    doc_id = data.get('doc_id')
    website_id = data.get('website_id')

    if not doc_id or not website_id:
        logger.error(f"❌ Missing doc_id or website_id in delete event: {data}")
        return

    try:
        delete_document_chunks(website_id=website_id, doc_id=doc_id)
        logger.info(f"🗑️  Deleted chunks for document {doc_id}")
    except Exception as exc:
        logger.error(f"❌ Failed to delete chunks for {doc_id}: {exc}", exc_info=True)


def start_consumer():
    consumer = get_consumer()
    topics = [
        os.environ.get('KAFKA_DOCUMENT_UPLOAD_TOPIC', 'document-upload'),
        'document-delete',
    ]
    consumer.subscribe(topics)
    logger.info(f"🚀 Kafka consumer started — listening on: {topics}")

    try:
        while True:
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                continue

            if msg.error():
                if msg.error().code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
                    print("Topic not ready yet, retrying...")
                    time.sleep(2)
                    continue
                else:
                    raise KafkaException(msg.error())

            topic = msg.topic()
            try:
                data = json.loads(msg.value().decode('utf-8'))
                logger.info(f"📥 Received event on [{topic}]: doc_id={data.get('doc_id')}")

                if topic == 'document-upload':
                    process_upload_event(data)
                elif topic == 'document-delete':
                    process_delete_event(data)
                else:
                    logger.warning(f"⚠️  Unknown topic: {topic}")

                # Only commit offset after successful processing
                consumer.commit(asynchronous=False)

            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to decode message: {e}")
                consumer.commit(asynchronous=False)

    except KeyboardInterrupt:
        logger.info("🛑 Consumer stopped by user")
    finally:
        consumer.close()
        logger.info("🔒 Consumer closed")


if __name__ == '__main__':
    start_consumer()