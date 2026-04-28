from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from .models import TenantUser
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from .serializers import UserSerializer
from django.conf import settings
import json


class GoogleAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('credential')
        
        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
            )
        except ValueError:
            return Response({'error': 'Invalid Google token'}, status=400)

        email = idinfo['email']
        name = idinfo.get('given_name', '')
        
        user, created = TenantUser.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0],
                'first_name': name,
            }
        )
        
        refresh = RefreshToken.for_user(user)
        user_data = UserSerializer(user).data
        
        response = Response({
            'success': True,
        }, status=201 if created else 200)
        
        # Auth token (httpOnly, secure)
        response.set_cookie(
            'authToken',
            str(refresh.access_token),
            max_age=3600,
            httponly=False,
            secure=True,
            samesite='None',  # Change this to None for cross-site
            path='/',
        )

        response.set_cookie(
            'user',
            json.dumps(user_data),
            max_age=3600 * 24 * 7,
            httponly=False,
            secure=True,
            samesite='None',  # Change this
            path='/',
        )

        response.set_cookie(
            'refreshToken',
            str(refresh),
            max_age=3600 * 24 * 7,
            httponly=False,
            secure=True,
            samesite='None',  # Change this
            path='/',
        )
        
        return response