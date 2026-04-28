"""
JwtCookieMiddleware
-------------------
Django Channels middleware that authenticates WebSocket connections
using the same `authToken` cookie that CookieJWTAuthentication uses
for HTTP requests.

Usage in asgi.py:
    from chat.jwt_middleware import JwtCookieMiddleware
    ...
    'websocket': JwtCookieMiddleware(
        URLRouter([...])
    ),
"""

from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


@database_sync_to_async
def get_user_from_token(token: str):
    try:
        jwt_auth = JWTAuthentication()
        validated = jwt_auth.get_validated_token(token)
        return jwt_auth.get_user(validated)
    except (InvalidToken, TokenError):
        return AnonymousUser()


class JwtCookieMiddleware:
    """
    Reads `authToken` from the WebSocket cookie header and populates
    scope['user'] with the authenticated Django user (or AnonymousUser).
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'websocket':
            headers = dict(scope.get('headers', []))
            cookie_header = headers.get(b'cookie', b'').decode('utf-8', errors='ignore')
            token = self._extract_cookie(cookie_header, 'authToken')

            if not token:
                query_string = scope.get('query_string', b'').decode()
                params = dict(p.split('=', 1) for p in query_string.split('&') if '=' in p)
                token = params.get('token')

            print(f"[JwtMiddleware] token found: {bool(token)}, token[:20]: {token[:20] if token else None}")

            if token:
                user = await get_user_from_token(token)
                print(f"[JwtMiddleware] user: {user}, is_authenticated: {getattr(user, 'is_authenticated', False)}")
                scope['user'] = user
            else:
                print("[JwtMiddleware] no token — AnonymousUser")
                scope['user'] = AnonymousUser()

        return await self.inner(scope, receive, send)

    @staticmethod
    def _extract_cookie(cookie_header: str, name: str) -> str | None:
        for part in cookie_header.split(';'):
            part = part.strip()
            if part.startswith(f'{name}='):
                return part[len(f'{name}='):]
        return None


#             | 172.18.0.1:50758 - - [24/Apr/2026:14:02:24] "WSDISCONNECT /ws/live-support/4e6f2e34-4bc7-4210-99d5-85708978222a/" - -
# chatbot_web             | [JwtMiddleware] user: laxmansu443@gmail.com, is_authenticated: True
# chatbot_web             | 172.18.0.1:49902 - - [24/Apr/2026:14:02:26] "GET /api/chat/5b591720-d387-48d1-a774-1cb8ddbb3b73/sessions/4e6f2e34-4bc7-4210-99d5-85708978222a/" 200 529
# chatbot_web             | 172.18.0.1:49882 - - [24/Apr/2026:14:02:26] "GET /api/chat/5