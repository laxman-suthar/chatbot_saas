from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.utils import timezone
from django.db.models import Q, Count
from websites.models import Website
from .models import ChatSession
from .serializers import ChatSessionSerializer, ChatSessionListSerializer


# ── Pagination ────────────────────────────────────────────────────────────────

class ChatSessionPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


# ── Views ─────────────────────────────────────────────────────────────────────

class ChatSessionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get_website(self, website_id, user):
        try:
            return Website.objects.get(id=website_id, owner=user)
        except Website.DoesNotExist:
            return None

    @extend_schema(
        tags=['Chat'],
        summary='List chat sessions for a website (paginated)',
        parameters=[
            OpenApiParameter(name='status', type=str, location=OpenApiParameter.QUERY,
                             enum=['active', 'closed'], required=False),
            OpenApiParameter(name='search', type=str, location=OpenApiParameter.QUERY,
                             required=False),
            OpenApiParameter(name='page', type=int, location=OpenApiParameter.QUERY,
                             required=False),
            OpenApiParameter(name='page_size', type=int, location=OpenApiParameter.QUERY,
                             required=False),
        ],
        responses={200: ChatSessionListSerializer(many=True)},
    )
    def get(self, request, website_id):
        website = self.get_website(website_id, request.user)
        if not website:
            return Response({'error': 'Website not found'}, status=status.HTTP_404_NOT_FOUND)

        sessions = (
            ChatSession.objects
            .filter(website=website)
            .prefetch_related('messages')
            .annotate(msg_count=Count('messages'))
        )

        status_param = request.query_params.get('status')
        if status_param == 'active':
            sessions = sessions.filter(is_active=True)
        elif status_param == 'closed':
            sessions = sessions.filter(is_active=False)

        search = request.query_params.get('search', '').strip()
        if search:
            sessions = sessions.filter(
                Q(visitor_name__icontains=search) | Q(visitor_email__icontains=search)
            )

        sessions = sessions.order_by('-created_at')

        paginator = ChatSessionPagination()
        page = paginator.paginate_queryset(sessions, request)
        serializer = ChatSessionListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class ChatSessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Chat'], summary='Get full chat session with messages',
                   responses={200: ChatSessionSerializer})
    def get(self, request, website_id, session_id):
        try:
            session = ChatSession.objects.get(id=session_id, website__owner=request.user)
            return Response(ChatSessionSerializer(session).data)
        except ChatSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(tags=['Chat'], summary='Delete a chat session', responses={204: None})
    def delete(self, request, website_id, session_id):
        try:
            session = ChatSession.objects.get(id=session_id, website__owner=request.user)
            session.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ChatSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)


class EndChatSessionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['Chat'], summary='Manually end a chat session',
                   responses={200: ChatSessionSerializer})
    def post(self, request, website_id, session_id):
        try:
            session = ChatSession.objects.get(id=session_id, website__owner=request.user)
            session.is_active = False
            session.ended_at = timezone.now()
            session.save()
            return Response(ChatSessionSerializer(session).data)
        except ChatSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)


class EscalatedSessionListView(APIView):
    """
    Returns all escalated sessions (waiting for or in live agent support).
    Used to show the queue of customers needing human help.
    GET /api/chat/escalated/
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Chat'],
        summary='List all escalated sessions awaiting or in live support',
        parameters=[
            OpenApiParameter(name='live_only', type=bool, location=OpenApiParameter.QUERY,
                             required=False, description='Filter to only sessions with active live agent'),
            OpenApiParameter(name='page', type=int, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: ChatSessionListSerializer(many=True)},
    )
    def get(self, request):
        sessions = (
            ChatSession.objects
            .filter(website__owner=request.user, is_escalated=True)
            .select_related('website')
            .prefetch_related('messages')
            .annotate(msg_count=Count('messages'))
            .order_by('-created_at')
        )

        live_only = request.query_params.get('live_only')
        if live_only == 'true':
            sessions = sessions.filter(is_live_agent_active=True)

        paginator = ChatSessionPagination()
        page = paginator.paginate_queryset(sessions, request)
        return paginator.get_paginated_response(
            ChatSessionListSerializer(page, many=True).data
        )


class LiveSupportSessionsView(APIView):
    """
    Returns escalated sessions that are currently active (waiting for or with agent).
    Used to show the live support inbox/queue.
    GET /api/chat/live-support/
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Chat'],
        summary='List live support sessions (escalated + active)',
        responses={200: ChatSessionListSerializer(many=True)},
    )
    def get(self, request):
        sessions = (
            ChatSession.objects
            .filter(
                website__owner=request.user,
                is_escalated=True,
                is_active=True,
            )
            .select_related('website')
            .prefetch_related('messages')
            .annotate(msg_count=Count('messages'))
            .order_by('-created_at')
        )

        serializer = ChatSessionListSerializer(sessions, many=True)
        return Response({
            'results': serializer.data,
            'count': sessions.count(),
        })
    
from rest_framework.views import APIView

from rest_framework.permissions import AllowAny

class WebSocketStatsView(APIView):
    """
    GET /api/chat/ws-stats/
    Returns count of active (open) and total WebSocket connections.
    No authentication required.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        active_sessions = ChatSession.objects.filter(is_active=True).count()
        total_sessions  = ChatSession.objects.count()

        return Response({
            "active_websockets": active_sessions,   # currently open / connected
            "total_sessions":    total_sessions,     # all sessions ever created
        })
    

class CreateChatSessionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        website_id = request.data.get('website_id')
        api_key = request.data.get('api_key')

        if not website_id or not api_key:
            return Response({'error': 'website_id and api_key are required.'}, status=400)

        try:
            website = Website.objects.get(id=website_id, api_key=api_key)
        except Website.DoesNotExist:
            return Response({'error': 'Invalid website_id or api_key.'}, status=401)

        visitor_ip = request.META.get('REMOTE_ADDR')
        session = ChatSession.objects.create(website=website, visitor_ip=visitor_ip)

        return Response({'session_id': str(session.id)}, status=201)
    

