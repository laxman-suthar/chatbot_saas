from django.contrib.auth.models import AbstractUser
from django.db import models


class TenantUser(AbstractUser):
    PLAN_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    ]
    email = models.EmailField(unique=True) 
    company_name = models.CharField(max_length=255, blank=True)
    plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        default='free'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email