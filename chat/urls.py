from django.urls import path
from .views import (
    ChatSessionListView,
    ChatSessionDetailView,
    EndChatSessionView
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
]