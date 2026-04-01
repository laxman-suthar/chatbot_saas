import requests
from celery import shared_task
from django.conf import settings


@shared_task(bind=True, max_retries=3)
def send_whatsapp_escalation(self, reason: str, session_id: str = None):
    """
    Send WhatsApp notification to support team
    when a chat is escalated
    """
    try:
        message = (
            f"🚨 *Escalation Alert*\n\n"
            f"Session ID: {session_id or 'N/A'}\n"
            f"Reason: {reason}\n\n"
            f"Please attend to this customer immediately."
        )

        response = requests.post(
            f"https://graph.facebook.com/v17.0/"
            f"{settings.WHATSAPP_PHONE_ID}/messages",
            headers={
                'Authorization': f"Bearer {settings.WHATSAPP_TOKEN}",
                'Content-Type': 'application/json'
            },
            json={
                'messaging_product': 'whatsapp',
                'to': settings.SUPPORT_WHATSAPP_NUMBER,
                'type': 'text',
                'text': {'body': message}
            },
            timeout=10
        )
        response.raise_for_status()

    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


@shared_task
def end_inactive_sessions():
    """
    Periodic task to close sessions
    inactive for more than 30 minutes
    """
    from django.utils import timezone
    from datetime import timedelta
    from .models import ChatSession

    cutoff = timezone.now() - timedelta(minutes=30)
    inactive_sessions = ChatSession.objects.filter(
        is_active=True,
        messages__timestamp__lt=cutoff
    ).distinct()

    count = inactive_sessions.update(
        is_active=False,
        ended_at=timezone.now()
    )
    print(f"Closed {count} inactive sessions")