from rest_framework import serializers
from .models import Website


class WebsiteSerializer(serializers.ModelSerializer):
    total_documents = serializers.SerializerMethodField()
    total_sessions = serializers.SerializerMethodField()

    class Meta:
        model = Website
        fields = [
            'id',
            'name',
            'domain',
            'api_key',
            'is_active',
            'total_documents',
            'total_sessions',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'api_key',
            'total_documents',
            'total_sessions',
            'created_at',
            'updated_at'
        ]

    def get_total_documents(self, obj):
        return obj.documents.count()

    def get_total_sessions(self, obj):
        return obj.chat_sessions.count()

    def validate_domain(self, value):
        # normalize domain — strip trailing slash
        value = value.rstrip('/')
        # check uniqueness excluding current instance
        qs = Website.objects.filter(domain=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'A website with this domain already exists'
            )
        return value


class WebsiteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Website
        fields = ['name', 'domain']

    def validate_domain(self, value):
        value = value.rstrip('/')
        if Website.objects.filter(domain=value).exists():
            raise serializers.ValidationError(
                'A website with this domain already exists'
            )
        return value


class EmbedScriptSerializer(serializers.Serializer):
    script_tag = serializers.CharField(read_only=True)
    api_key = serializers.UUIDField(read_only=True)
    websocket_url = serializers.CharField(read_only=True)