from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from .models import TenantUser
from rest_framework.views import APIView
from rest_framework.permissions import  AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from .serializers import  UserSerializer
from django.conf import settings

class GoogleAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('credential')  # Google ID token from frontend
        
        try:
            # Verify the Google token
            idinfo = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
            )
        except ValueError:
            return Response({'error': 'Invalid Google token'}, status=400)

        email = idinfo['email']
        name = idinfo.get('given_name', '')
        
        # Get or create user
        user, created = TenantUser.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0],
                'first_name': name,
            }
        )
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=201 if created else 200)