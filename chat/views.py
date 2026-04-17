from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from django.utils import timezone
from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter
from websites.models import Website
from .models import ChatSession
from .serializers import (
    ChatSessionSerializer,
    ChatSessionListSerializer
)


class ChatSessionListView(APIView):
    permission_classes = [IsAuthenticated]
 
    def get_website(self, website_id, user):
        try:
            return Website.objects.get(id=website_id, owner=user)
        except Website.DoesNotExist:
            return None
 
    @extend_schema(
        tags=['Chat'],
        summary='List all chat sessions for a website',
        parameters=[
            OpenApiParameter(
                name='status',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by session status: active or closed',
                required=False,
                enum=['active', 'closed'],
            ),
            OpenApiParameter(
                name='search',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Search by visitor name or email',
                required=False,
            ),
        ],
        responses={200: ChatSessionListSerializer(many=True)},
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
 
        # Filter by status
        status_param = request.query_params.get('status')
        if status_param in ('active', 'closed'):
            if status_param =='active':

                sessions = sessions.filter(is_active=True)
            else:
                sessions = sessions.filter(is_active=False)
 
        # Search by visitor name or email (case-insensitive)
        search = request.query_params.get('search', '').strip()
        if search:
            sessions = sessions.filter(
                Q(visitor_name__icontains=search) |
                Q(visitor_email__icontains=search)
            )
 
        sessions = sessions.order_by('-created_at')
 
        return Response(
            ChatSessionListSerializer(sessions, many=True).data
        )


class ChatSessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Chat'],
        summary='Get full chat session with messages',
        responses={200: ChatSessionSerializer}
    )
    def get(self, request, website_id, session_id):
        try:
            session = ChatSession.objects.get(
                id=session_id,
                website__owner=request.user
            )
            return Response(
                ChatSessionSerializer(session).data
            )
        except ChatSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @extend_schema(
        tags=['Chat'],
        summary='Delete a chat session',
        responses={204: None}
    )
    def delete(self, request, website_id, session_id):
        try:
            session = ChatSession.objects.get(
                id=session_id,
                website__owner=request.user
            )
            session.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ChatSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class EndChatSessionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Chat'],
        summary='Manually end a chat session',
        responses={200: ChatSessionSerializer}
    )
    def post(self, request, website_id, session_id):
        try:
            session = ChatSession.objects.get(
                id=session_id,
                website__owner=request.user
            )
            session.is_active = False
            session.ended_at = timezone.now()
            session.save()
            return Response(
                ChatSessionSerializer(session).data
            )
        except ChatSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )