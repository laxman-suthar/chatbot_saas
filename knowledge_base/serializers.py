from rest_framework import serializers
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    file_size_kb = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id',
            'title',
            'file',
            'file_type',
            'file_size',
            'file_size_kb',
            'status',
            'error_message',
            'chunk_count',
            'uploaded_at',
            'processed_at',
        ]
        read_only_fields = [
            'id',
            'file_type',
            'file_size',
            'file_size_kb',
            'status',
            'error_message',
            'chunk_count',
            'uploaded_at',
            'processed_at',
        ]

    def get_file_size_kb(self, obj):
        return round(obj.file_size / 1024, 2) if obj.file_size else 0


class DocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['title', 'file']

    def validate_file(self, value):
        allowed_types = [
            'application/pdf',
            'text/plain',
            'application/msword',
            'application/vnd.openxmlformats-officedocument'
            '.wordprocessingml.document'
        ]
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                'Only PDF, TXT, DOC, DOCX files are allowed'
            )
        # max 10MB
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError(
                'File size must be under 10MB'
            )
        return value