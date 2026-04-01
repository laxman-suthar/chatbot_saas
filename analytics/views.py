from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.utils import timezone
from django.db.models import (
    Count,
    Avg,
    Q,
    F,
    ExpressionWrapper,
    DurationField
)
from django.db.models.functions import TruncDate
from datetime import timedelta, date

from websites.models import Website
from chat.models import ChatSession, Message
from knowledge_base.models import Document
from .serializers import (
    ConversationSerializer,
    WebsiteStatsSerializer,
    DailyStatsSerializer,
    TopQuestionsSerializer,)


class WebsiteStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get_website(self, website_id, user):
        try:
            return Website.objects.get(id=website_id, owner=user)
        except Website.DoesNotExist:
            return None

    @extend_schema(
        tags=['Analytics'],
        summary='Get overall stats for a website',
        responses={200: WebsiteStatsSerializer}
    )
    def get(self, request, website_id):
        website = self.get_website(website_id, request.user)
        if not website:
            return Response(
                {'error': 'Website not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        now = timezone.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # session stats
        sessions = ChatSession.objects.filter(website=website)
        total_sessions = sessions.count()
        active_sessions = sessions.filter(is_active=True).count()
        total_escalations = sessions.filter(is_escalated=True).count()

        # message stats
        total_messages = Message.objects.filter(
            session__website=website
        ).count()

        # averages
        avg_messages = round(
            total_messages / total_sessions, 2
        ) if total_sessions else 0

        # avg session duration
        completed_sessions = sessions.filter(
            ended_at__isnull=False
        ).annotate(
            duration=ExpressionWrapper(
                F('ended_at') - F('created_at'),
                output_field=DurationField()
            )
        )
        avg_duration = 0
        if completed_sessions.exists():
            total_seconds = sum(
                s.duration.total_seconds()
                for s in completed_sessions
            )
            avg_duration = round(
                total_seconds / 60 / completed_sessions.count(), 2
            )

        # escalation rate
        escalation_rate = round(
            (total_escalations / total_sessions * 100), 2
        ) if total_sessions else 0

        # document stats
        documents = Document.objects.filter(website=website)
        total_documents = documents.count()
        processed_documents = documents.filter(status='processed').count()
        failed_documents = documents.filter(status='failed').count()

        # time-based session counts
        sessions_today = sessions.filter(
            created_at__date=today
        ).count()
        sessions_this_week = sessions.filter(
            created_at__date__gte=week_ago
        ).count()
        sessions_this_month = sessions.filter(
            created_at__date__gte=month_ago
        ).count()

        return Response({
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'total_messages': total_messages,
            'total_escalations': total_escalations,
            'escalation_rate': escalation_rate,
            'avg_messages_per_session': avg_messages,
            'avg_session_duration_minutes': avg_duration,
            'total_documents': total_documents,
            'processed_documents': processed_documents,
            'failed_documents': failed_documents,
            'sessions_today': sessions_today,
            'sessions_this_week': sessions_this_week,
            'sessions_this_month': sessions_this_month,
        })


class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get_website(self, website_id, user):
        try:
            return Website.objects.get(id=website_id, owner=user)
        except Website.DoesNotExist:
            return None

    @extend_schema(
        tags=['Analytics'],
        summary='List all conversations for a website',
        parameters=[
            OpenApiParameter(
                name='escalated',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter escalated sessions only',
                required=False
            ),
            OpenApiParameter(
                name='from_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter from date (YYYY-MM-DD)',
                required=False
            ),
            OpenApiParameter(
                name='to_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter to date (YYYY-MM-DD)',
                required=False
            ),
            OpenApiParameter(
                name='is_active',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter active sessions only',
                required=False
            ),
        ],
        responses={200: ConversationSerializer(many=True)}
    )
    def get(self, request, website_id):
        website = self.get_website(website_id, request.user)
        if not website:
            return Response(
                {'error': 'Website not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        sessions = ChatSession.objects.filter(
            website=website
        ).prefetch_related('messages')

        # filters
        escalated = request.query_params.get('escalated')
        if escalated is not None:
            sessions = sessions.filter(
                is_escalated=escalated.lower() == 'true'
            )

        is_active = request.query_params.get('is_active')
        if is_active is not None:
            sessions = sessions.filter(
                is_active=is_active.lower() == 'true'
            )

        from_date = request.query_params.get('from_date')
        if from_date:
            sessions = sessions.filter(
                created_at__date__gte=from_date
            )

        to_date = request.query_params.get('to_date')
        if to_date:
            sessions = sessions.filter(
                created_at__date__lte=to_date
            )

        return Response(
            ConversationSerializer(sessions, many=True).data
        )


class DailyStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get_website(self, website_id, user):
        try:
            return Website.objects.get(id=website_id, owner=user)
        except Website.DoesNotExist:
            return None

    @extend_schema(
        tags=['Analytics'],
        summary='Get daily session stats for last 30 days',
        parameters=[
            OpenApiParameter(
                name='days',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Number of days to look back (default 30)',
                required=False
            ),
        ],
        responses={200: DailyStatsSerializer(many=True)}
    )
    def get(self, request, website_id):
        website = self.get_website(website_id, request.user)
        if not website:
            return Response(
                {'error': 'Website not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        days = int(request.query_params.get('days', 30))
        from_date = timezone.now().date() - timedelta(days=days)

        # sessions grouped by date
        daily_sessions = (
            ChatSession.objects
            .filter(website=website, created_at__date__gte=from_date)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                sessions=Count('id'),
                escalations=Count('id', filter=Q(is_escalated=True))
            )
            .order_by('date')
        )

        # messages grouped by date
        daily_messages = (
            Message.objects
            .filter(
                session__website=website,
                timestamp__date__gte=from_date
            )
            .annotate(date=TruncDate('timestamp'))
            .values('date')
            .annotate(messages=Count('id'))
        )

        # merge into dict by date
        messages_by_date = {
            item['date']: item['messages']
            for item in daily_messages
        }

        result = []
        for item in daily_sessions:
            result.append({
                'date': item['date'],
                'sessions': item['sessions'],
                'messages': messages_by_date.get(item['date'], 0),
                'escalations': item['escalations'],
            })

        return Response(result)


class TopQuestionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get_website(self, website_id, user):
        try:
            return Website.objects.get(id=website_id, owner=user)
        except Website.DoesNotExist:
            return None

    @extend_schema(
        tags=['Analytics'],
        summary='Get most frequently asked questions',
        parameters=[
            OpenApiParameter(
                name='limit',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Number of questions to return (default 10)',
                required=False
            ),
        ],
        responses={200: TopQuestionsSerializer(many=True)}
    )
    def get(self, request, website_id):
        website = self.get_website(website_id, request.user)
        if not website:
            return Response(
                {'error': 'Website not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        limit = int(request.query_params.get('limit', 10))

        top_questions = (
            Message.objects
            .filter(
                session__website=website,
                role='user'
            )
            .values('content')
            .annotate(count=Count('content'))
            .order_by('-count')[:limit]
        )

        return Response(list(top_questions))