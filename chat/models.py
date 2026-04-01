import uuid
from django.db import models
from websites.models import Website


class ChatSession(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    website = models.ForeignKey(
        Website,
        on_delete=models.CASCADE,
        related_name='chat_sessions'
    )
    visitor_ip = models.GenericIPAddressField(null=True, blank=True)
    visitor_name = models.CharField(max_length=255, blank=True)
    visitor_email = models.EmailField(blank=True)
    is_escalated = models.BooleanField(default=False)
    escalation_reason = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Session {self.id} — {self.website.name}"


class Message(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"
    

class RequestCallback(models.Model):
    SUBJECT_CHOICES = [
        ('general', 'General Inquiry'),
        ('support', 'Technical Support'),
        ('billing', 'Billing & Payments'),
        ('sales', 'Sales & Pricing'),
        ('complaint', 'Complaint'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='callback_requests',
        null=True,
        blank=True
    )
    website = models.ForeignKey(
        Website,
        on_delete=models.CASCADE,
        related_name='callback_requests'
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20)
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES, default='general')
    reason = models.TextField(blank=True)
    is_contacted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['-created_at']
 
    def __str__(self):
        return f"{self.name} — {self.phone} ({self.website.name})"