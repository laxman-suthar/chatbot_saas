import json
import logging
from confluent_kafka import Producer
from django.conf import settings

logger = logging.getLogger(__name__)


def get_kafka_producer() -> Producer:
    return Producer({
        'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
        'client.id': 'django-producer',
        'acks': 'all',
        'retries': 3,
    })


def delivery_callback(err, msg):
    if err:
        logger.error(f'❌ Message delivery failed: {err}')
    else:
        logger.info(f'✅ Message delivered to {msg.topic()} [{msg.partition()}]')


def produce_document_upload(doc_id: str, website_id: str, file_path: str = None,
                            text_content: str = None, doc_type: str = 'file', 
                            title: str = '', filename: str = None):
    """Produce a document-upload event to Kafka"""
    producer = get_kafka_producer()

    message = {
        'doc_id': doc_id,
        'website_id': website_id,
        'file_path': file_path,
        'text_content': text_content,
        'doc_type': doc_type,
        'title': title,
        'filename': filename,  # ✅ Include filename for unique storage
    }

    producer.produce(
        topic=settings.KAFKA_DOCUMENT_UPLOAD_TOPIC,
        key=str(doc_id).encode('utf-8'),
        value=json.dumps(message).encode('utf-8'),
        callback=delivery_callback,
    )
    producer.flush(timeout=10)
    logger.info(f"📤 Produced document-upload event for {doc_id} (filename={filename})")


def produce_document_delete(doc_id: str, website_id: str):
    """Produce a document-delete event to Kafka so consumer cleans ChromaDB"""
    producer = get_kafka_producer()

    message = {
        'doc_id': doc_id,
        'website_id': website_id,
        'action': 'delete',
    }

    producer.produce(
        topic='document-delete',
        key=str(doc_id).encode('utf-8'),
        value=json.dumps(message).encode('utf-8'),
        callback=delivery_callback,
    )
    producer.flush(timeout=10)
    logger.info(f"📤 Produced document-delete event for {doc_id}")