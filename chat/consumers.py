import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import ChatSession, Message, RequestCallback
from .agent import build_agent, ESCALATION_SENTINEL, wants_human_agent
from websites.models import Website


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.website_id = self.scope['url_route']['kwargs']['website_id']

        query_string = self.scope.get('query_string', b'').decode()
        params = dict(
            param.split('=') for param in query_string.split('&')
            if '=' in param
        )
        api_key = params.get('api_key', '')

        self.website = await self.get_website(self.website_id, api_key)

        if not self.website:
            await self.close(code=4001)
            return

        visitor_ip = self.scope.get('client', [None])[0]
        self.session = await self.create_session(visitor_ip)

        self.agent = build_agent(
            website_id=str(self.website_id),
            session_id=str(self.session.id)
        )

        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'session_id': str(self.session.id),
            'message': f"Hello! Welcome to {self.website.name} support. How can I help you today?",
            'role': 'assistant'
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'session'):
            await self.end_session()

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)

            # ── Handle callback form submission ──────────────────
            if data.get('type') == 'callback_form':
                name    = data.get('name', '').strip()
                email   = data.get('email', '').strip()
                phone   = data.get('phone', '').strip()
                subject = data.get('subject', 'general').strip()

                if not name or not email or not phone:
                    await self.send(text_data=json.dumps({
                        'type': 'callback_form_error',
                        'message': 'Please fill in all required fields.'
                    }))
                    return

                await self.save_callback(name, email, phone, subject)

                await self.send(text_data=json.dumps({
                    'type': 'callback_form_success',
                    'role': 'assistant',
                    'message': (
                        f"Thank you, {name}! ✅\n\n"
                        f"We've received your request and our team will reach out to you shortly. "
                        f"Is there anything else I can help you with?"
                    )
                }))
                return

            # ── Normal chat message ──────────────────────────────
            user_message = data.get('message', '').strip()
            if not user_message:
                return

            await self.save_message('user', user_message)

            await self.send(text_data=json.dumps({
                'type': 'typing',
                'message': 'Agent is typing...'
            }))

            # Fast AI intent check — catches any phrasing before running the full agent
            is_human_request = await database_sync_to_async(wants_human_agent)(user_message)
            if is_human_request:
                await self.send(text_data=json.dumps({
                    'type': 'callback_form_request',
                    'message': "Sure! Please share your details and our team will get back to you."
                }))
                return

            response = await database_sync_to_async(
                self.agent.invoke
            )({'input': user_message})

            ai_response = response.get('output', 'I am unable to process your request right now.')

            # Fallback: if the ReAct agent still used EscalateToHuman tool
            if ESCALATION_SENTINEL in ai_response:
                await self.send(text_data=json.dumps({
                    'type': 'callback_form_request',
                    'message': "Sure! Please share your details and our team will get back to you."
                }))
                return

            await self.save_message('assistant', ai_response)

            await self.send(text_data=json.dumps({
                'type': 'message',
                'role': 'assistant',
                'message': ai_response,
                'session_id': str(self.session.id)
            }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid message format'
            }))

        except Exception as e:
            print(f"AGENT ERROR: {str(e)}", flush=True)
            import traceback
            traceback.print_exc()
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Something went wrong. Please try again.'
            }))

    # ─── Database Helpers ────────────────────────────

    @database_sync_to_async
    def get_website(self, website_id, api_key):
        try:
            return Website.objects.get(
                id=website_id,
                api_key=api_key,
                is_active=True
            )
        except Website.DoesNotExist:
            return None

    @database_sync_to_async
    def create_session(self, visitor_ip):
        return ChatSession.objects.create(
            website=self.website,
            visitor_ip=visitor_ip
        )

    @database_sync_to_async
    def save_message(self, role, content):
        return Message.objects.create(
            session=self.session,
            role=role,
            content=content
        )

    @database_sync_to_async
    def save_callback(self, name, email, phone, subject):
        return RequestCallback.objects.create(
            session=self.session,
            website=self.website,
            name=name,
            email=email,
            phone=phone,
            subject=subject,
        )

    @database_sync_to_async
    def end_session(self):
        self.session.is_active = False
        self.session.ended_at = timezone.now()
        self.session.save()