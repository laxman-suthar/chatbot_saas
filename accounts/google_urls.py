from django.urls import path
from .google_views import GoogleAuthView
app_name = 'social'
urlpatterns = [
       path('google/', GoogleAuthView.as_view(), name='google-auth'),
]