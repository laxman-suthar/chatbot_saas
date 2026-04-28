from django.urls import path
from .views import (
    ChatSessionListView,
    ChatSessionDetailView,
    EndChatSessionView,
    EscalatedSessionListView,
    LiveSupportSessionsView,
    WebSocketStatsView,
    CreateChatSessionView

)

urlpatterns = [
    # list all sessions for a website
    path(
        '<uuid:website_id>/sessions/',
        ChatSessionListView.as_view(),
        name='chat-session-list'
    ),
    # get + delete specific session
    path(
        '<uuid:website_id>/sessions/<uuid:session_id>/',
        ChatSessionDetailView.as_view(),
        name='chat-session-detail'
    ),
    # manually end a session
    path(
        '<uuid:website_id>/sessions/<uuid:session_id>/end/',
        EndChatSessionView.as_view(),
        name='chat-session-end'
    ),
       # All escalated sessions waiting for or in live agent support
    path(
        'escalated/',
        EscalatedSessionListView.as_view(),
        name='escalated-session-list'
    ),
    # Active live support sessions (agent already connected)
    path(
        'live-support/',
        LiveSupportSessionsView.as_view(),
        name='live-support-session-list'
    ),
    path('ws-stats/', WebSocketStatsView.as_view(), name='ws-stats'),
    path('session/', CreateChatSessionView.as_view(), name='create-chat-session'),
]