from django.urls import path
from .views import (
    WebsiteStatsView,
    ConversationListView,
    DailyStatsView,
    TopQuestionsView
)

urlpatterns = [
    # overall stats
    path(
        '<uuid:website_id>/stats/',
        WebsiteStatsView.as_view(),
        name='website-stats'
    ),
    # all conversations with filters
    path(
        '<uuid:website_id>/conversations/',
        ConversationListView.as_view(),
        name='conversation-list'
    ),
    # daily stats chart data
    path(
        '<uuid:website_id>/daily-stats/',
        DailyStatsView.as_view(),
        name='daily-stats'
    ),
    # top questions asked
    path(
        '<uuid:website_id>/top-questions/',
        TopQuestionsView.as_view(),
        name='top-questions'
    ),
]