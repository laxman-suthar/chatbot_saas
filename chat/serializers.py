from rest_framework import serializers
from .models import ChatSession, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            'id',
            'role',
            'content',
            'timestamp',
        ]
        read_only_fields = ['id', 'timestamp']


class ChatSessionSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()
    website_name = serializers.SerializerMethodField()
    website_id = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = [
            'id',
            'website_id',
            'website_name',
            'visitor_ip',
            'visitor_name',
            'visitor_email',
            'is_escalated',
            'escalation_reason',
            'is_active',
            'is_live_agent_active',
            'message_count',
            'messages',
            'created_at',
            'ended_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_message_count(self, obj):
        return obj.messages.count()

    def get_website_name(self, obj):
        return obj.website.name if obj.website else ''

    def get_website_id(self, obj):
        return str(obj.website.id) if obj.website else ''


class ChatSessionListSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    website_name = serializers.SerializerMethodField()
    website_id = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = [
            'id',
            'website_id',
            'website_name',
            'visitor_ip',
            'visitor_name',
            'visitor_email',
            'is_escalated',
            'is_active',
            'is_live_agent_active',
            'message_count',
            'last_message',
            'created_at',
            'ended_at',
        ]

    def get_message_count(self, obj):
        return obj.messages.count()

    def get_last_message(self, obj):
        last = obj.messages.last()
        if last:
            return {
                'role': last.role,
                'content': last.content[:100],
                'timestamp': last.timestamp,
            }
        return None

    def get_website_name(self, obj):
        return obj.website.name if obj.website else ''

    def get_website_id(self, obj):
        return str(obj.website.id) if obj.website else ''