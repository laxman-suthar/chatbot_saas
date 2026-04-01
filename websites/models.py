import uuid
from django.db import models
from accounts.models import TenantUser


class Website(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    owner = models.ForeignKey(
        TenantUser,
        on_delete=models.CASCADE,
        related_name='websites'
    )
    name = models.CharField(max_length=255)
    domain = models.URLField(unique=True)
    api_key = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} — {self.domain}"