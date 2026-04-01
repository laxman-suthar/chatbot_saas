from rest_framework import serializers
from .models import ChatSession, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            'id',
            'role',
            'content',
            'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class ChatSessionSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = [
            'id',
            'visitor_ip',
            'visitor_name',
            'visitor_email',
            'is_escalated',
            'escalation_reason',
            'is_active',
            'message_count',
            'messages',
            'created_at',
            'ended_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_message_count(self, obj):
        return obj.messages.count()


class ChatSessionListSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = [
            'id',
            'visitor_ip',
            'visitor_name',
            'visitor_email',
            'is_escalated',
            'is_active',
            'message_count',
            'last_message',
            'created_at',
            'ended_at'
        ]

    def get_message_count(self, obj):
        return obj.messages.count()

    def get_last_message(self, obj):
        last = obj.messages.last()
        if last:
            return {
                'role': last.role,
                'content': last.content[:100],
                'timestamp': last.timestamp
            }
        return None