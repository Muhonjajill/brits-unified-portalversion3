# core/tasks.py

import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from core.models import Ticket, EscalationHistory
from core.utilss.escalation_constants import ESCALATION_TIME_LIMITS, ESCALATION_FLOW
from core.utilss.escalation_rules import escalate_ticket, send_escalation_email, send_unassigned_ticket_notification, is_within_working_hours


logger = logging.getLogger(__name__)


def send_escalation_notification(ticket):
    """
    Broadcast a WebSocket notification to notify users about ticket escalation.
    """
    channel_layer = get_channel_layer()
    message = {
        "ticket_id": ticket.id,
        "title": ticket.title,
        "priority": ticket.priority,
        "escalated_at": ticket.escalated_at.strftime("%Y-%m-%d %H:%M") if ticket.escalated_at else "",
    }
    async_to_sync(channel_layer.group_send)(
        "escalations",
        {"type": "escalation_message", "message": message}
    )

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_auto_escalation(self):
    """Periodic task that checks tickets for unassigned notifications and escalations."""
    now = timezone.now()
    logger.info(f"Auto-escalation check started at {now}")

    tickets = Ticket.objects.filter(status__in=['open', 'in_progress'])

    for ticket in tickets:
        ticket = Ticket.objects.get(id=ticket.id)

        logger.debug(
            f"Checking ticket {ticket.id}: "
            f"Escalation={ticket.current_escalation_level}, "
            f"Assigned={ticket.assigned_to}, Priority={ticket.priority}"
        )

        if ticket.assigned_to:
            if is_within_working_hours():
                escalate_ticket(ticket)
            else:
                logger.info(f"Escalation for ticket {ticket.id} skipped (outside working hours).")
        else:
            send_unassigned_ticket_notification(ticket)
