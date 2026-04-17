from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'website',
        'doc_type',
        'status',
        'file_size',
        'chunk_count',
        'uploaded_at',
    )
    list_filter = ('status', 'doc_type', 'uploaded_at', 'website')
    search_fields = ('title', 'website__name')
    readonly_fields = (
        'id',
        'file_size',
        'chunk_count',
        'uploaded_at',
        'processed_at',
        'file_type',
    )
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'title', 'website', 'doc_type')
        }),
        ('File Details', {
            'fields': ('file', 'file_type', 'file_size'),
            'classes': ('collapse',)
        }),
        ('Text Content', {
            'fields': ('text_content',),
            'classes': ('collapse',)
        }),
        ('Processing', {
            'fields': ('status', 'error_message', 'chunk_count', 'uploaded_at', 'processed_at'),
            'classes': ('collapse',)
        }),
    )