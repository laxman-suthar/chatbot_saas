from django.contrib import admin
from .models import Website


@admin.register(Website)
class WebsiteAdmin(admin.ModelAdmin):
    list_display = ['name', 'domain', 'owner', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'domain', 'owner__email']
    readonly_fields = ['id', 'api_key', 'created_at', 'updated_at']
    ordering = ['-created_at']