import uuid
from django.db import models
from accounts.models import TenantUser
from pgvector.django import VectorField
from websites.models import Website

class Document(models.Model):
    """Uploaded documents (file or text)"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    ]
    
    DOC_TYPE_CHOICES = [
        ('file', 'File Upload'),
        ('text', 'Text Paste'),
    ]
 
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    website = models.ForeignKey(
        Website,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    title = models.CharField(max_length=255)
    file = models.FileField(
        upload_to='documents/%Y/%m/%d/',
        null=True,
        blank=True
    )
    file_type = models.CharField(max_length=20, blank=True)
    file_size = models.PositiveIntegerField(default=0)  # in bytes
    
    doc_type = models.CharField(
        max_length=20,
        choices=DOC_TYPE_CHOICES,
        default='file',
        help_text='Whether document was uploaded as file or pasted text'
    )
    text_content = models.TextField(
        null=True,
        blank=True,
        help_text='Raw text content for text-paste uploads'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    error_message = models.TextField(blank=True)
    chunk_count = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
 
    class Meta:
        ordering = ['-uploaded_at']
        db_table = 'knowledge_base_document'
 
    def __str__(self):
        return f"{self.title} — {self.website.name}"
 
 
class DocumentChunk(models.Model):
    """Individual chunks with embeddings stored in pgvector"""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='chunks'
    )
    website = models.ForeignKey(
        Website,
        on_delete=models.CASCADE,
        related_name='chunks'
    )
    content = models.TextField()
    embedding = VectorField(dimensions=1536)  # pgvector field
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['website', 'document']),
            models.Index(fields=['website']),
        ]
        db_table = 'knowledge_base_documentchunk'
 
    def __str__(self):
        return f"Chunk from {self.document.title}"
 