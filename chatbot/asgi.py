import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot.settings')
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import re_path
from chat.consumers import ChatConsumer
from chat.notification_consumer import NotificationConsumer
from chat.jwt_middleware import JwtCookieMiddleware

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': URLRouter([

        # ── Public — visitor widget (auth handled inside consumer via api_key) ──
        re_path(r'ws/chat/(?P<website_id>[^/]+)/(?P<session_id>[^/]+)/$', JwtCookieMiddleware(ChatConsumer.as_asgi())),

      
        re_path(r'ws/notifications/$',
            JwtCookieMiddleware(NotificationConsumer.as_asgi())),
    ]),
})