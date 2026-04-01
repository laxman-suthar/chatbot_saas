from rest_framework import serializers
from chat.models import ChatSession, Message


class ConversationSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    duration_minutes = serializers.SerializerMethodField()

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
            'last_message',
            'duration_minutes',
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
                'timestamp': last.timestamp
            }
        return None

    def get_duration_minutes(self, obj):
        if obj.ended_at and obj.created_at:
            delta = obj.ended_at - obj.created_at
            return round(delta.total_seconds() / 60, 2)
        return None


class WebsiteStatsSerializer(serializers.Serializer):
    total_sessions = serializers.IntegerField()
    active_sessions = serializers.IntegerField()
    total_messages = serializers.IntegerField()
    total_escalations = serializers.IntegerField()
    escalation_rate = serializers.FloatField()
    avg_messages_per_session = serializers.FloatField()
    avg_session_duration_minutes = serializers.FloatField()
    total_documents = serializers.IntegerField()
    processed_documents = serializers.IntegerField()
    failed_documents = serializers.IntegerField()
    sessions_today = serializers.IntegerField()
    sessions_this_week = serializers.IntegerField()
    sessions_this_month = serializers.IntegerField()


class DailyStatsSerializer(serializers.Serializer):
    date = serializers.DateField()
    sessions = serializers.IntegerField()
    messages = serializers.IntegerField()
    escalations = serializers.IntegerField()


class TopQuestionsSerializer(serializers.Serializer):
    content = serializers.CharField()
    count = serializers.IntegerField()