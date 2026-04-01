from django.urls import path
from .views import (
    DocumentListUploadView,
    DocumentDetailView,
    ReprocessDocumentView
)

urlpatterns = [
    # list + upload documents
    path(
        '<uuid:website_id>/documents/',
        DocumentListUploadView.as_view(),
        name='document-list-upload'
    ),
    # get + delete document
    path(
        '<uuid:website_id>/documents/<uuid:doc_id>/',
        DocumentDetailView.as_view(),
        name='document-detail'
    ),
    # reprocess failed document
    path(
        '<uuid:website_id>/documents/<uuid:doc_id>/reprocess/',
        ReprocessDocumentView.as_view(),
        name='document-reprocess'
    ),
]