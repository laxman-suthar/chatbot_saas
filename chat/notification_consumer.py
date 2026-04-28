import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatSession


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    One persistent connection per logged-in portal user.
    Receives escalation notifications and handles accept/reject.
    URL: ws/notifications/
    """

    async def connect(self):
        user = self.scope.get('user')

        await self.accept()

        if not user or not user.is_authenticated:
            await self.close(code=4003)
            return

        self.user = user
        self.group_name = f"notify_user_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """
        Portal agent sends accept or reject for an escalation.

        Accept:  { "type": "accept", "session_id": "<uuid>" }
        Reject:  { "type": "reject", "session_id": "<uuid>" }
        """
        try:
            data = json.loads(text_data)
            msg_type = data.get('type')
            session_id = data.get('session_id', '').strip()

            if not session_id:
                return

            # Verify this session belongs to the logged-in user
            valid = await self.session_belongs_to_user(session_id, self.user)
            if not valid:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Session not found.',
                }))
                return

            if msg_type == 'accept':
                # Confirm to portal — frontend will router.push to live-support page
                # agent_joined fires automatically when LiveSupportConsumer connects
                await self.send(text_data=json.dumps({
                    'type': 'accept_confirmed',
                    'session_id': session_id,
                }))

            elif msg_type == 'reject':
                # Push rejection event to visitor's ChatConsumer via session group
                await self.channel_layer.group_send(
                    f"session_{session_id}",
                    {'type': 'agent_rejected'}
                )
                # Confirm to portal
                await self.send(text_data=json.dumps({
                    'type': 'reject_confirmed',
                    'session_id': session_id,
                }))

        except json.JSONDecodeError:
            pass

    # ── Called by channel_layer.group_send from ChatConsumer._trigger_escalation
    async def notify_escalation(self, event):
        """Forward escalation notification to the portal frontend."""
        await self.send(text_data=json.dumps({
            'type': 'escalation',
            'session_id': event['session_id'],
            'visitor_name': event.get('visitor_name', 'Anonymous'),
            'website_name': event.get('website_name', ''),
            'timestamp': event.get('timestamp', ''),
        }))

    # ── DB helpers ────────────────────────────────────────────────────────────

    @database_sync_to_async
    def session_belongs_to_user(self, session_id, user):
        return ChatSession.objects.filter(
            id=session_id,
            website__owner=user,
        ).exists()