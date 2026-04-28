import json
import logging
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import ChatSession, Message
from .agent import build_agent, ESCALATION_SENTINEL, wants_human_agent
from .utils import anonymize_for_llm

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.website_id  = self.scope['url_route']['kwargs']['website_id']
        self.session_id  = self.scope['url_route']['kwargs']['session_id']
        self.session     = None
        self.room_group  = None
        self.is_live_agent        = False
        self.is_live_agent_active = False
        self.agent_already_active = False
        self.agent_name  = None
        self.escalated   = False

        self.collecting_fields = False
        self.required_fields   = []
        self.collected_fields  = {}

        user = self.scope.get('user')
        print(user)

        # ── Live agent joining ───────────────────────────────────────────────
        if user and user.is_authenticated:
            logger.info(f"🔵 [AGENT] {user.email} attempting to join session {self.session_id}")

            self.session = await self.get_session_for_user(self.session_id, user)
            if not self.session:
                logger.warning(f"❌ [AGENT] Session {self.session_id} not found for user {user.email}")
                await self.close(code=4004)
                return

            if not self.session.is_active:
                logger.warning(f"❌ [AGENT] Session {self.session_id} is inactive")
                await self.accept()
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Visitor has already left this session.'
                }))
                await self.close(code=4005)
                return

            if self.session.is_live_agent_active:
                logger.warning(f"❌ [AGENT] Session {self.session_id} already has an active agent")
                await self.accept()
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Another agent is already handling this session.'
                }))
                await self.close(code=4006)
                return

            self.is_live_agent = True
            self.agent_name    = user.get_full_name() or user.email
            await self.accept()

            self.room_group = f"session_{self.session_id}"
            await self.channel_layer.group_add(self.room_group, self.channel_name)
            await self.set_live_agent_active(True)

            logger.info(f"✅ [AGENT] {self.agent_name} joined session {self.session_id} | group: {self.room_group}")

            messages = await self.get_messages()
            logger.info(f"📜 [AGENT] Sending {len(messages)} history messages to agent")
            await self.send(text_data=json.dumps({
                'type': 'history',
                'messages': messages,
            }))

            await self.channel_layer.group_send(
                self.room_group,
                {'type': 'agent_joined', 'agent_name': self.agent_name}
            )
            logger.info(f"📣 [AGENT] agent_joined sent to group {self.room_group}")
            return

        # ── Visitor connecting ───────────────────────────────────────────────
        logger.info(f"🟢 [VISITOR] Connecting to session {self.session_id}")

        self.session = await self.get_session(self.session_id)
        if not self.session:
            logger.warning(f"❌ [VISITOR] Session {self.session_id} not found → closing 4010")
            await self.close(code=4010)
            return
        headers = dict(self.scope.get('headers', []))
        origin  = headers.get(b'origin', b'').decode('utf-8', errors='ignore').rstrip('/')
        website_domain = await database_sync_to_async(
            lambda: self.session.website.domain.rstrip('/')
        )()

        if origin and origin != website_domain:
            logger.warning(f"❌ [VISITOR] Origin mismatch | origin={origin} | domain={website_domain}")
            await self.close(code=4003)
            return

        logger.info(f"✅ [VISITOR] Origin validated | origin={origin}")
        self.escalated            = self.session.is_escalated
        self.is_live_agent_active = self.session.is_live_agent_active
        self.agent_already_active = False

        if self.session.visitor_details:
            self.collected_fields = self.session.visitor_details

        logger.info(
            f"✅ [VISITOR] Session loaded | "
            f"escalated={self.escalated} | "
            f"is_live_agent_active={self.is_live_agent_active} | "
            f"collected_fields={bool(self.collected_fields)}"
        )

        await self.accept()

        self.room_group = f"session_{self.session_id}"
        await self.channel_layer.group_add(self.room_group, self.channel_name)
        logger.info(f"📌 [VISITOR] Joined group {self.room_group}")

        self.agent = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: build_agent(
                website_id=str(self.website_id),
                session_id=str(self.session_id),
            ),
        )

        messages = await self.get_messages()
        if messages:
            logger.info(f"📜 [VISITOR] Loading {len(messages)} history messages")
            await self._load_history_into_agent(messages)
            await self.send(text_data=json.dumps({
                'type': 'history',
                'messages': messages,
            }))
        else:
            logger.info(f"👋 [VISITOR] Fresh session — sending greeting")
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'session_id': str(self.session.id),
                'message': f"Hello! Welcome to {self.session.website.name} support. How can I help you today?",
                'role': 'assistant',
            }))

    async def disconnect(self, close_code):
        if not self.room_group:
            return

        if self.is_live_agent:
            logger.info(f"🔴 [AGENT] {self.agent_name} disconnected from session {self.session_id}")
            await self.reset_escalation()
            await self.channel_layer.group_send(
                self.room_group,
                {'type': 'agent_disconnected'}
            )
            await self.set_live_agent_active(False)
        else:
            logger.info(f"🔴 [VISITOR] Disconnected | is_live_agent_active={self.is_live_agent_active}")
            if self.is_live_agent_active:
                logger.info(f"📣 [VISITOR] Notifying agent — visitor left")
                await self.channel_layer.group_send(
                    self.room_group,
                    {'type': 'visitor_left'}
                )

        await self.channel_layer.group_discard(self.room_group, self.channel_name)
        logger.info(f"🚪 Removed from group {self.room_group}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)

            # ── Live agent ────────────────────────────────────────────────────
            if self.is_live_agent:
                msg_type = data.get('type')
                logger.info(f"📨 [AGENT] {self.agent_name} sent type={msg_type}")

                if msg_type == 'message':
                    message = data.get('message', '').strip()
                    if not message:
                        return
                    await self.save_message('agent', message)
                    logger.info(f"💬 [AGENT] Message saved | group_send to {self.room_group}")
                    await self.channel_layer.group_send(
                        self.room_group,
                        {'type': 'agent_message', 'message': message, 'agent_name': self.agent_name}
                    )
                    await self.send(text_data=json.dumps({
                        'type': 'message_sent',
                        'message': message,
                        'agent_name': self.agent_name,
                    }))

                elif msg_type == 'end_chat':
                    logger.info(f"🛑 [AGENT] {self.agent_name} ended chat")
                    await self.set_live_agent_active(False)
                    await self.reset_escalation()
                    await self.channel_layer.group_send(
                        self.room_group,
                        {'type': 'agent_disconnected'}
                    )
                    await self.send(text_data=json.dumps({
                        'type': 'chat_ended',
                        'message': 'Live chat session ended.',
                    }))
                return

            # ── Visitor ───────────────────────────────────────────────────────
            user_message = data.get('message', '').strip()
            if not user_message:
                return

            logger.info(
                f"📨 [VISITOR] Message | "
                f"is_live_agent_active={self.is_live_agent_active} | "
                f"collecting={self.collecting_fields} | "
                f"escalated={self.escalated}"
            )

            if self.is_live_agent_active:
                logger.info(f"🔁 [VISITOR] Relaying to agent group {self.room_group}")
                await self.save_message('user', user_message)
                await self.channel_layer.group_send(
                    self.room_group,
                    {'type': 'visitor_message', 'message': user_message}
                )
                return

            if self.collecting_fields:
                for field in self.required_fields:
                    key = field.get('key') if isinstance(field, dict) else field
                    if key not in self.collected_fields:
                        self.collected_fields[key] = user_message
                        logger.info(f"📋 [FIELD] Collected '{key}' = '{user_message}'")
                        await self.save_message('user', user_message)
                        await self._ask_next_field()
                        return

            await self.save_message('user', user_message)
            await self.send(text_data=json.dumps({'type': 'typing', 'message': 'Thinking...'}))

            is_human_request = await database_sync_to_async(wants_human_agent)(user_message)
            logger.info(f"🤔 [VISITOR] is_human_request={is_human_request} | escalated={self.escalated}")

            if is_human_request and not self.escalated:
                await self._trigger_escalation()
                return

            if is_human_request and self.escalated:
                required_fields = await self.get_required_fields()
                if required_fields and not self.collected_fields:
                    self.collecting_fields = True
                    self.required_fields   = required_fields
                    self.collected_fields  = {}
                    msg = "We still need a few quick details before connecting you. 📋"
                    await self.save_message('system', msg)
                    await self.send(text_data=json.dumps({'type': 'waiting_for_agent', 'message': msg}))
                    await self._ask_next_field()
                else:
                    msg = "You're already in the queue! 🙏 An agent will be with you shortly. Feel free to keep asking in the meantime."
                    await self.save_message('assistant', msg)
                    await self.send(text_data=json.dumps({'type': 'message', 'role': 'assistant', 'message': msg}))
                    await self._notify_agent()
                return

            logger.info(f"🤖 [AI] Invoking agent for session {self.session_id}")
            ai_response = None

            try:
                response = await asyncio.wait_for(
                    database_sync_to_async(self.agent.invoke)({'input': user_message}),
                    timeout=60.0,
                )
                ai_response = response.get('output', '').strip()
                logger.info(f"✅ [AI] Response received | length={len(ai_response)}")

            except IndexError:
                logger.warning(f"⚠️ [AI] IndexError — empty response")
                ai_response = "Hey there! 👋 How can I help you today?"
            except asyncio.TimeoutError:
                logger.error(f"⏱️ [AI] Timeout")
                await self.send(text_data=json.dumps({'type': 'error', 'message': 'Response took too long. Please try again.'}))
                return
            except Exception:
                import traceback; traceback.print_exc()
                await self.send(text_data=json.dumps({'type': 'error', 'message': 'Something went wrong. Please try again.'}))
                return

            if not ai_response:
                ai_response = "I'm here to help! Could you tell me more about what you need?"

            if ESCALATION_SENTINEL in ai_response and not self.escalated:
                await self._trigger_escalation()
                return

            await self.save_message('assistant', ai_response)
            await self.send(text_data=json.dumps({
                'type': 'message', 'role': 'assistant',
                'message': ai_response, 'session_id': str(self.session.id),
            }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'Invalid message format'}))

    # ─────────────────────────────────────────────────────────────────────────
    #  Escalation
    # ─────────────────────────────────────────────────────────────────────────

    async def _trigger_escalation(self):
        if self.escalated:
            return
        self.escalated = True
        await self.mark_escalated()
        logger.info(f"🚨 [ESCALATION] Triggered for session {self.session_id}")

        required_fields  = await self.get_required_fields()
        existing_details = await self.get_visitor_details()

        if required_fields and not existing_details:
            self.collecting_fields = True
            self.required_fields   = required_fields
            self.collected_fields  = {}
            logger.info(f"📋 [ESCALATION] Starting field collection — {len(required_fields)} fields")
            msg = "We've raised your concern! Before connecting you with an agent, I just need a few quick details. 📋"
            await self.save_message('system', msg)
            await self.send(text_data=json.dumps({'type': 'waiting_for_agent', 'message': msg}))
            await self._ask_next_field()
        else:
            self.collected_fields = existing_details or {}
            logger.info(f"♻️ [ESCALATION] Reusing existing details: {self.collected_fields}")
            if existing_details:
                msg = "We've raised your concern — an agent will be with you ASAP. Meanwhile, feel free to keep asking! 🙏"
                await self.save_message('system', msg)
                await self.send(text_data=json.dumps({'type': 'waiting_for_agent', 'message': msg}))
            await self._notify_agent()

    async def _ask_next_field(self):
        for field in self.required_fields:
            key         = field.get('key')             if isinstance(field, dict) else field
            label       = field.get('label', key)      if isinstance(field, dict) else key
            description = field.get('description', '') if isinstance(field, dict) else ''

            if key not in self.collected_fields:
                question = f"{label}? ℹ️ {description}" if description else f"Could you provide your {label}?"
                logger.info(f"❓ [FIELD] Asking '{key}'")
                await self.save_message('assistant', question)
                await self.send(text_data=json.dumps({'type': 'message', 'role': 'assistant', 'message': question}))
                return

        self.collecting_fields = False
        await self.save_visitor_details(self.collected_fields)
        logger.info(f"✅ [FIELD] All collected: {self.collected_fields}")
        confirmation = "Perfect! Thank you. 🙏 An agent will be with you shortly. Meanwhile feel free to keep asking!"
        await self.save_message('system', confirmation)
        await self.send(text_data=json.dumps({'type': 'waiting_for_agent', 'message': confirmation}))
        await self._notify_agent()

    async def _notify_agent(self):
        owner_id     = await database_sync_to_async(lambda: self.session.website.owner_id)()
        website_name = await database_sync_to_async(lambda: self.session.website.name)()

        if not self.collected_fields:
            msg = "We've raised your concern — an agent will be with you ASAP. Meanwhile, feel free to keep asking! 🙏"
            await self.save_message('system', msg)
            await self.send(text_data=json.dumps({'type': 'waiting_for_agent', 'message': msg}))

        logger.info(f"📣 [NOTIFY] Sending to owner {owner_id} | details={self.collected_fields}")
        await self.channel_layer.group_send(
            f"notify_user_{owner_id}",
            {
                'type':            'notify.escalation',
                'session_id':      str(self.session.id),
                'visitor_details': self.collected_fields,
                'website_name':    website_name,
                'timestamp':       timezone.now().isoformat(),
            }
        )

    # ─────────────────────────────────────────────────────────────────────────
    #  Group message handlers
    # ─────────────────────────────────────────────────────────────────────────

    async def agent_joined(self, event):
        self.is_live_agent_active = True
        logger.info(f"📣 [GROUP] agent_joined | is_live_agent={self.is_live_agent} | agent_already_active={self.agent_already_active}")
        if not self.is_live_agent and not self.agent_already_active:
            await self.send(text_data=json.dumps({
                'type': 'agent_joined',
                'message': (
                    f"{event.get('agent_name', 'A support agent')} has joined the chat. "
                    "Feel free to share your concern! 😊"
                ),
                'agent_name': event.get('agent_name', 'Support Agent'),
            }))
        self.agent_already_active = False

    async def agent_message(self, event):
        self.is_live_agent_active = True
        logger.info(f"📣 [GROUP] agent_message | is_live_agent={self.is_live_agent} | channel={self.channel_name}")
        if not self.is_live_agent:
            await self.send(text_data=json.dumps({
                'type': 'agent_message',
                'role': 'human_agent',
                'message': event['message'],
                'agent_name': event.get('agent_name', 'Support Agent'),
            }))

    async def agent_rejected(self, event):
        await self.send(text_data=json.dumps({
            'type': 'agent_rejected',
            'message': "We're sorry, our team is currently unavailable. Please try again later. 😔",
        }))

    async def agent_disconnected(self, event):
        self.is_live_agent_active = False
        self.escalated = False
        logger.info(f"📣 [GROUP] agent_disconnected | is_live_agent={self.is_live_agent}")
        if not self.is_live_agent:
            await self.send(text_data=json.dumps({
                'type': 'agent_disconnected',
                'message': "The support agent has ended the session. Is there anything else I can help you with?",
            }))

    async def visitor_message(self, event):
        logger.info(f"📣 [GROUP] visitor_message | is_live_agent={self.is_live_agent}")
        if self.is_live_agent:
            await self.send(text_data=json.dumps({
                'type': 'visitor_message',
                'message': event['message'],
            }))

    async def visitor_left(self, event):
        logger.info(f"📣 [GROUP] visitor_left | is_live_agent={self.is_live_agent}")
        if self.is_live_agent:
            await self.send(text_data=json.dumps({
                'type': 'visitor_left',
                'message': 'Visitor has disconnected.',
            }))
            await self.close()

    # ─────────────────────────────────────────────────────────────────────────
    #  DB helpers
    # ─────────────────────────────────────────────────────────────────────────

    @database_sync_to_async
    def get_session(self, session_id):
        try:
            return ChatSession.objects.select_related('website').get(id=session_id)
        except ChatSession.DoesNotExist:
            return None

    @database_sync_to_async
    def get_session_for_user(self, session_id, user):
        try:
            return ChatSession.objects.select_related('website__owner').get(
                id=session_id, website__owner=user,
            )
        except ChatSession.DoesNotExist:
            return None

    @database_sync_to_async
    def get_messages(self):
        return [
            {
                'id':        str(m.id),
                'role':      m.role,
                'content':   m.content,
                'timestamp': m.timestamp.isoformat(),
            }
            for m in Message.objects.filter(
                session_id=self.session_id
            ).order_by('timestamp')
        ]

    @database_sync_to_async
    def save_message(self, role, content):
        return Message.objects.create(session=self.session, role=role, content=content)

    @database_sync_to_async
    def mark_escalated(self):
        self.session.is_escalated      = True
        self.session.escalation_reason = 'Visitor requested human agent'
        self.session.save(update_fields=['is_escalated', 'escalation_reason'])

    @database_sync_to_async
    def end_session(self):
        self.session.is_active = False
        self.session.ended_at  = timezone.now()
        self.session.save(update_fields=['is_active', 'ended_at'])

    @database_sync_to_async
    def set_live_agent_active(self, value: bool):
        ChatSession.objects.filter(id=self.session_id).update(is_live_agent_active=value)

    @database_sync_to_async
    def reset_escalation(self):
        ChatSession.objects.filter(id=self.session_id).update(
            is_escalated=False,
            escalation_reason=''
        )

    @database_sync_to_async
    def get_required_fields(self):
        from django.core.cache import cache
        cache_key    = f"website_{self.website_id}"
        website_data = cache.get(cache_key)
        if website_data is None:
            website_data = {
                'required_fields': list(self.session.website.required_fields or []),
                'name':            self.session.website.name,
            }
            cache.set(cache_key, website_data, timeout=3600)
        return website_data['required_fields']

    @database_sync_to_async
    def save_visitor_details(self, details):
        ChatSession.objects.filter(id=self.session_id).update(visitor_details=details)

    @database_sync_to_async
    def get_visitor_details(self):
        session = ChatSession.objects.get(id=self.session_id)
        return session.visitor_details or {}

    async def _load_history_into_agent(self, messages):
        details = self.session.visitor_details or {}

        def _load(msgs):
            for i in range(0, len(msgs) - 1, 2):
                human = msgs[i]
                ai    = msgs[i + 1] if i + 1 < len(msgs) else None
                if human['role'] == 'user' and ai and ai['role'] in ('assistant', 'agent'):
                    self.agent.memory.save_context(
                        {'input':  anonymize_for_llm(human['content'], details)},
                        {'output': anonymize_for_llm(ai['content'], details)},
                    )

        logger.info(f"🧠 [MEMORY] Loading {len(messages)} messages into agent memory")
        await asyncio.get_event_loop().run_in_executor(None, lambda: _load(messages))