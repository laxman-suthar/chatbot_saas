"""
Custom authentication that checks for JWT token in cookies.
Add this file to your accounts app.
"""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed as JWTAuthenticationFailed


class CookieJWTAuthentication(BaseAuthentication):
    """
    Authenticates by looking for JWT token in cookies.
    Falls back to Authorization header if no cookie found.
    """
    
    def authenticate(self, request):
        # Try to get token from cookies first
        token = request.COOKIES.get('authToken')
        
        # If not in cookies, try Authorization header (standard JWT)
        if not token:
            auth_header = request.META.get('HTTP_AUTHORIZATION', '').split()
            if len(auth_header) == 2 and auth_header[0].lower() == 'bearer':
                token = auth_header[1]
        
        # If still no token, return None (let other auth methods handle it)
        if not token:
            return None
        
        # Validate the token using JWT authentication
        try:
            jwt_auth = JWTAuthentication()
            # Create a fake request with the token in Authorization header
            request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
            validated_token = jwt_auth.get_validated_token(token)
            user = jwt_auth.get_user(validated_token)
            return (user, validated_token)
        except (InvalidToken, JWTAuthenticationFailed) as e:
            raise AuthenticationFailed(f'Invalid or expired token: {str(e)}')