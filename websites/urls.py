from django.urls import path
from .views import (
    WebsiteListCreateView,
    WebsiteDetailView,
    RegenerateAPIKeyView,
    ToggleWebsiteStatusView,
    EmbedScriptView,
    ResolveWebsiteView,
)

urlpatterns = [
    # list + create
    path(
        '',
        WebsiteListCreateView.as_view(),
        name='website-list-create'
    ),
    # just check for setup 
    path('resolve/', ResolveWebsiteView.as_view()),
    # detail + update + delete
    path(
        '<uuid:website_id>/',
        WebsiteDetailView.as_view(),
        name='website-detail'
    ),
    # regenerate api key
    path(
        '<uuid:website_id>/regenerate-key/',
        RegenerateAPIKeyView.as_view(),
        name='regenerate-api-key'
    ),
    # toggle active status
    path(
        '<uuid:website_id>/toggle-status/',
        ToggleWebsiteStatusView.as_view(),
        name='toggle-website-status'
    ),
    # get embed script
    path(
        '<uuid:website_id>/embed-script/',
        EmbedScriptView.as_view(),
        name='embed-script'
    ),

    
]