from rest_framework import serializers
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    website_name = serializers.CharField(source='website.name', read_only=True)
    
    class Meta:
        model = Document
        fields = [
            'id',
            'website',
            'website_name',
            'title',
            'file', 
            'file_type',
            'file_size',
            'doc_type',
            'status',
            'error_message',
            'chunk_count',
            'uploaded_at',
            'processed_at',
        ]
        read_only_fields = [
            'id',
            'website_name',
            'file_type',
            'file_size',
            'chunk_count',
            'uploaded_at',
            'processed_at',
            'error_message',
            'status',
        ]


class DocumentUploadSerializer(serializers.ModelSerializer):
    """
    Serializer for file uploads only.
    For text uploads, use the API directly with JSON.
    """
    class Meta:
        model = Document
        fields = ['title', 'file']
    
    def validate_file(self, value):
        """Validate file size (max 10MB)"""
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size exceeds 10MB limit. Current size: {value.size / 1024 / 1024:.2f}MB"
            )
        
        # Validate file type
        allowed_types = [
            'application/pdf',
            'text/plain',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        ]
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f"File type not supported. Allowed: PDF, TXT, DOC, DOCX"
            )
        
        return value
    
    def create(self, validated_data):
        """Create document with doc_type='file'"""
        validated_data['doc_type'] = 'file'
        return super().create(validated_data)