import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot.settings')

# ← setup django BEFORE importing anything else
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from chat.consumers import ChatConsumer

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter([
            path('ws/chat/<uuid:website_id>/', ChatConsumer.as_asgi()),
        ])
    ),
})