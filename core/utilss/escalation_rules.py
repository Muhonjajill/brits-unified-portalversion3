#escalation_rules.py
import pytz
from django.utils import timezone 
from datetime import timedelta


#from core.models import EscalationHistory
from django.core.mail import send_mail
from django.conf import settings

# core/utilss/escalation_rules.py
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from core.uttils.serializers import serialize_ticket
from core.utilss.escalation_constants import ESCALATION_TIME_LIMITS, ESCALATION_FLOW


import logging

# Initialize the logger
logger = logging.getLogger(__name__)


ESCALATION_MATRIX = {
    'technical outage': {
        'low': "Tier 1 handles. Escalates to Tier 2 if unresolved in 8 hours. Director alerted.",
        'medium': "Tier 1 updates every 2 hrs. Escalates to Director + Country Manager after 2 hrs.",
        'high': "Auto-escalated. Support alerts Director immediately. MD is briefed.",
        'critical': '"All-hands" mode. Director leads, MD oversees. War room initiated.',
    },
    'cybersecurity incident': {
        'low': "Support investigates. Escalates to Director if compliance risk suspected.",
        'medium': "Escalated to Director and Country Manager. Risk assessment begins.",
        'high': "Protocol triggered. Director and MD notified. Forensics initiated.",
        'critical': "Full incident response team. MD leads client/regulator comms. 24/7 bridge opened.",
    },
    'client complaint': {
        'low': "Handled by Support. Logged as feedback.",
        'medium': "Escalated to Country Manager. Director informed.",
        'high': "Country Manager + Director involved. MD briefed.",
        'critical': "MD and Director lead full service review. All teams mobilized.",
    },
    'sla breach': {
        'low': "Director investigates. Engineer resolves.",
        'medium': "Director investigates. Country Manager briefed.",
        'high': "Director starts RCA. MD informed.",
        'critical': "MD leads executive intervention. Recovery roadmap created.",
    }
}

CATEGORY_TO_ESCALATION_TYPE = {
    'Hardware Related': 'technical outage',
    'Software Related': 'technical outage',
    'Cash Reconciliation': 'technical outage',
    'Power and Network': 'technical outage',
    'De-/Installation /Maintenance': 'technical outage',
    'Safe': 'technical outage',
    'SLA Related': 'SLA Breach',
    'Other': 'Client Complaint'
}


TIER_MAPPING = {
    'low': 'Tier 1',
    'medium': 'Tier 1',
    'high': 'Tier 1',
    'critical': 'Tier 1',
}

ESCALATION_FLOW = {
    'Tier 1': 'Tier 2',
    'Tier 2': 'Tier 3',
    'Tier 3': 'Tier 4',
    'Tier 4': None,
}

MAX_ESCALATION_LEVEL = {
    'low': 'Tier 3',
    'medium': 'Tier 3',
    'high': 'Tier 3',
    'critical': 'Tier 4',
}

ZONE_PRIORITY_THRESHOLDS = {
    'Zone A': {
        'critical': timedelta(minutes=2),
        'high': timedelta(minutes=5),
        'medium': timedelta(minutes=8),
        'low': timedelta(minutes=10),
    },
    'Zone B': {
        'critical': timedelta(minutes=6),
        'high': timedelta(minutes=7),
        'medium': timedelta(minutes=9),
        'low': timedelta(minutes=10),
    },
    'Zone C': {
        'critical': timedelta(minutes=8),
        'high': timedelta(minutes=9),
        'medium': timedelta(minutes=11),
        'low': timedelta(minutes=12),
    },
    'Zone D': {
        'critical': timedelta(minutes=10),
        'high': timedelta(minutes=11),
        'medium': timedelta(minutes=13),
        'low': timedelta(minutes=14),
    },
    'Zone E': {
        'critical': timedelta(minutes=12),
        'high': timedelta(minutes=13),
        'medium': timedelta(minutes=15),
        'low': timedelta(minutes=16),
    },
}




def send_unassigned_ticket_notification(ticket):
    now = timezone.now()

    PRIORITY_THRESHOLDS = {
        'low': timedelta(minutes=8),
        'medium': timedelta(minutes=6),
        'high': timedelta(minutes=4),
        'critical': timedelta(minutes=2),
    }

    priority = (ticket.priority or "low").lower()
    threshold = PRIORITY_THRESHOLDS.get(priority, timedelta(minutes=8))

    if not ticket.assigned_to:
        elapsed = now - ticket.created_at

        # 🔹 FIRST ROUND — if ticket just passed threshold and no notification sent yet
        if not ticket.last_unassigned_notification and elapsed >= threshold:
            _trigger_unassigned_alert(ticket, now)

        # 🔹 SUBSEQUENT ROUNDS — check repeat intervals
        elif ticket.last_unassigned_notification and now >= ticket.last_unassigned_notification + threshold:
            _trigger_unassigned_alert(ticket, now)


def _trigger_unassigned_alert(ticket, now):
    """Send WebSocket + Email alert for unassigned ticket."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "escalations",
        {
            "type": "unassigned_ticket_notification",
            "ticket": serialize_ticket(ticket),
        }
    )

    subject = f"[Unassigned Ticket] Ticket #{ticket.id} ({ticket.priority.capitalize()} Priority)"
    message = (
        f"Ticket #{ticket.id} ({ticket.priority.capitalize()} priority) is still unassigned.\n\n"
        f"- Created At: {ticket.created_at}\n"
        f"- Current Status: {ticket.status}\n\n"
        f"Please assign this ticket as soon as possible."
    )

    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [settings.EMAIL_HOST_USER])
        logger.info(f"✅ Unassigned ticket email sent for Ticket #{ticket.id}")
    except Exception as e:
        logger.error(f"❌ Failed to send unassigned ticket email for Ticket #{ticket.id}: {str(e)}")

    ticket.last_unassigned_notification = now
    ticket.save(update_fields=["last_unassigned_notification"])



def send_ticket_assignment_notification(ticket):
    """Send notification to admins or assigned staff to assign the ticket."""
    message = f"Ticket #{ticket.id} is not assigned yet. Please assign it within 2 hours."
    subject = "Unassigned Ticket Reminder"

    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [settings.EMAIL_HOST_USER])
        logger.info(f"Email sent successfully for Ticket #{ticket.id}")
    except Exception as e:
        logger.error(f"Failed to send email for Ticket #{ticket.id}: {str(e)}")

    # WebSocket notification
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "ticket_notifications",
        {"type": "ticket_assignment_notification", "message": message}
    )



def is_within_working_hours():
    nairobi_tz = pytz.timezone("Africa/Nairobi")
    now = timezone.now().astimezone(nairobi_tz)

    weekday = now.weekday()
    hour = now.hour

    return weekday < 5 and 9 <= hour <= 17



def escalate_ticket(ticket):

    from core.models import Zone, Ticket

    now = timezone.now()
    escalation_level = ticket.current_escalation_level or 'Tier 1'

    if not ticket.zone:
        logger.warning(f"Ticket {ticket.id} has no zone. Defaulting to Zone A.")
        ticket.zone, _ = Zone.objects.get_or_create(name='Zone A')

    if not is_within_working_hours():
        logger.info(f"⏸ Escalation skipped for Ticket {ticket.id} (outside working hours).")
        return

    # 🚫 Do not escalate unassigned tickets
    if not ticket.assigned_to or not ticket.assigned_at:
        logger.info(f"⏸ Escalation skipped for Ticket {ticket.id} (not yet assigned).")
        return

    zone_name = ticket.zone.name
    priority = (ticket.priority or "low").lower()

    zone_thresholds = ZONE_PRIORITY_THRESHOLDS.get(zone_name, ZONE_PRIORITY_THRESHOLDS['Zone A'])
    escalation_time = zone_thresholds.get(priority, timedelta(minutes=10))

    last_escalation_time = ticket.escalated_at

    # 🔹 FIRST ROUND — only after assigned_at
    if not last_escalation_time and now >= ticket.assigned_at + escalation_time:
        _do_escalation(ticket, escalation_level, now)

    # 🔹 SUBSEQUENT ROUNDS
    elif last_escalation_time and now >= last_escalation_time + escalation_time:
        _do_escalation(ticket, escalation_level, now)

def _do_escalation(ticket, escalation_level, now):
    from core.models import EscalationHistory

    priority = (ticket.priority or "low").lower()
    max_level = MAX_ESCALATION_LEVEL.get(priority, "Tier 3")

    # 🚫 Stop escalation if already at or beyond max allowed level
    if escalation_level == max_level:
        logger.info(
            f"⏹ Ticket {ticket.id} ({priority}) reached its max escalation level ({max_level})."
        )
        return

    next_level = ESCALATION_FLOW.get(escalation_level)
    if not next_level:
        logger.info(f"Ticket {ticket.id} already at highest escalation level ({escalation_level}).")
        return

    # 🔹 SLA BREACH CHECK (insert here)
    if ticket.due_date and not ticket.resolved_at and now > ticket.due_date:
        ticket.is_sla_breached = True
        logger.info(f"🚨 SLA breach detected for Ticket {ticket.id}")

    # Existing escalation update
    ticket.current_escalation_level = next_level
    ticket.is_escalated = True
    ticket.escalated_at = now
    ticket.save(update_fields=["current_escalation_level", "is_sla_breached", "is_escalated", "escalated_at"])

    send_escalation_email(ticket, next_level)
    EscalationHistory.objects.create(
        ticket=ticket,
        from_level=escalation_level,
        to_level=next_level,
        note=f"Auto-escalated at {priority} priority in {ticket.zone.name}."
    )

    logger.info(f"🚀 Ticket {ticket.id} escalated from {escalation_level} → {next_level}")




def get_escalation_recipients(level):
    
    emails = settings.ESCALATION_LEVEL_EMAILS.get(level)
    if emails:
        return list(emails)  
    return [settings.DEFAULT_FROM_EMAIL]

def get_email_for_level(level):
    return [settings.ESCALATION_LEVEL_EMAILS.get(level, (None,))[0]]  

def send_escalation_email(ticket, to_level):
    subject = f"[Escalation Notice] Ticket #{ticket.id} escalated to {to_level}"
    message = f"""
    Ticket ID: {ticket.id}
    Title: {ticket.title}
    Priority: {ticket.priority}
    Category: {ticket.problem_category}
    New Escalation Level: {to_level}
    Status: {ticket.status}
    Created At: {ticket.created_at}

    This ticket has been auto-escalated based on your escalation policy.

    Please log in to review.

    - Blue River Technology Solutions
    """
    recipients = get_escalation_recipients(to_level)
    send_mail(subject, message, None, recipients)