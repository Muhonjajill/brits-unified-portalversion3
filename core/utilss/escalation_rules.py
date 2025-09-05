#escalation_rules.py
from django.utils import timezone  # ✅ correct
from datetime import timedelta
from core.models import Zone, Ticket
from core.models import EscalationHistory



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

def send_unassigned_ticket_notification(ticket):
    """Send periodic notifications if ticket is not assigned within the threshold."""
    now = timezone.now()

    # Notification condition if the ticket is unassigned
    if not ticket.assigned_to and now >= ticket.created_at + timedelta(minutes=2):
        # Send a WebSocket notification to inform users about unassigned tickets
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "escalations",  # Group name
            {
                "type": "unassigned_ticket_notification",
                "ticket": serialize_ticket(ticket),  
            }
        )


def send_ticket_assignment_notification(ticket):
    """Send notification to admins or assigned staff to assign the ticket."""
    message = f"Ticket #{ticket.id} is not assigned yet. Please assign it within 2 hours."
    send_mail("Unassigned Ticket Reminder", message, None, [settings.ADMIN_EMAIL])

    # WebSocket notification
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "ticket_notifications",
        {"type": "ticket_assignment_notification", "message": message}
    )


def escalate_ticket(ticket):
    now = timezone.now()
    escalation_level = ticket.current_escalation_level or 'Tier 1'

    if not ticket.zone:
        logger.warning(f"Ticket {ticket.id} has no zone defined. Assigning default zone 'A'.")
        try:
            ticket.zone = Zone.objects.get(name='Zone A')
        except Zone.DoesNotExist:
            ticket.zone = Zone.objects.create(name='Zone A')

    if ticket.zone.name == 'Zone A':
        zone_threshold = timedelta(minutes=5)
    elif ticket.zone.name == 'Zone B':
        zone_threshold = timedelta(minutes=10)
    elif ticket.zone.name == 'Zone C':
        zone_threshold = timedelta(minutes=15)
    else:
        zone_threshold = timedelta(minutes=5)

    threshold_hours = ESCALATION_TIME_LIMITS.get(ticket.priority.lower(), 1)
    priority_threshold = timedelta(hours=threshold_hours)

    escalation_time = min(priority_threshold, zone_threshold)

    last_escalation_time = ticket.escalated_at or ticket.created_at

    if now >= last_escalation_time + escalation_time:
        logger.info(f"Ticket {ticket.id} exceeds escalation time. Proceeding with escalation.")

        if ticket.priority.lower() == 'critical':
            if escalation_level != 'Tier 4':
                next_level = ESCALATION_FLOW.get(escalation_level)
            else:
                next_level = None
        else:
            next_level = ESCALATION_FLOW.get(escalation_level)

        if next_level:
            logger.info(f"Ticket {ticket.id} escalated from {escalation_level} → {next_level}")

            ticket.current_escalation_level = next_level
            ticket.is_escalated = True
            ticket.escalated_at = now  
            ticket.save()

            send_escalation_email(ticket, next_level)

            EscalationHistory.objects.create(
                ticket=ticket,
                from_level=escalation_level,
                to_level=next_level,
                note=f"Auto-escalated based on zone {ticket.zone.name} "
                     f"and priority {ticket.priority}."
            )
        else:
            logger.info(f"Ticket {ticket.id} cannot be escalated further (already at Tier 4).")
    else:
        logger.info(f"Ticket {ticket.id} has not yet exceeded escalation time. No escalation.")





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