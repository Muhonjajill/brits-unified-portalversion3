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
from django.contrib.auth.models import User 


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

#ESCALATION TIME AS PER ZONES AND PRIORITIES
ZONE_PRIORITY_THRESHOLDS = {
    'Zone A': {
        'critical': timedelta(hours=2),
        'high': timedelta(hours=4),
        'medium': timedelta(hours=4),
        'low': timedelta(hours=6),
    },
    'Zone B': {
        'critical': timedelta(hours=4),
        'high': timedelta(hours=6),
        'medium': timedelta(hours=6),
        'low': timedelta(hours=8),
    },
    'Zone C': {
        'critical': timedelta(hours=6),
        'high': timedelta(hours=14),
        'medium': timedelta(hours=14),
        'low': timedelta(hours=24),
    },
    'Zone D': {
        'critical': timedelta(hours=6),
        'high': timedelta(hours=30),
        'medium': timedelta(hours=30),
        'low': timedelta(hours=48),
    },
}


"""def send_new_ticket_notification(ticket):

    # 🔹 Push WebSocket event
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "escalations",
        {
            "type": "new_ticket_notification",
            "ticket": serialize_ticket(ticket),
        }
    )

    subject = f"[New Ticket] Ticket #{ticket.id} Created"
    message = (
        f"A new ticket has been created.\n\n"
        f"- Ticket ID: {ticket.id}\n"
        f"- Title: {ticket.title}\n"
        f"- Priority: {ticket.priority}\n"
        f"- Category: {ticket.problem_category}\n"
        f"- Status: {ticket.status}\n"
        f"- Created At: {ticket.created_at}\n\n"
        f"Please review and assign it."
    )

    # 🔹 Collect recipients from groups
    recipients = list(
        User.objects.filter(groups__name__in=["Admin", "Director", "Manager", "Staff"])
        .exclude(email__isnull=True)
        .values_list("email", flat=True)
    )

    # 🔹 If no recipients, try fallback
    if not recipients:
        logger.warning("⚠️ No staff/admin recipients found for new ticket notification.")
        recipients = getattr(settings, "FALLBACK_NEW_TICKET_RECIPIENTS", [])

    # 🔹 Absolute last fallback
    if not recipients:
        recipients = [settings.DEFAULT_FROM_EMAIL]
        logger.warning(f"⚠️ Using DEFAULT_FROM_EMAIL as recipient: {recipients}")

    # 🔹 Get sender
    sender = getattr(settings, "NEW_TICKET_SENDER", settings.DEFAULT_FROM_EMAIL)

    try:
        logger.info(f"📧 Sending new ticket email for Ticket #{ticket.id}")
        logger.info(f"   From: {sender}")
        logger.info(f"   To: {recipients}")
        send_mail(subject, message, sender, recipients)
        logger.info(f"New ticket email sent for Ticket #{ticket.id} to {recipients}")
    except Exception as e:
        logger.error(f"Failed to send new ticket email for Ticket #{ticket.id}: {str(e)}")"""

def send_new_ticket_notification(ticket):
    """Notify admins/staff when a new ticket is created."""
    from django.urls import reverse
    from django.core.mail import EmailMultiAlternatives
    
    # WebSocket notification
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "escalations",
        {
            "type": "new_ticket_notification",
            "ticket": serialize_ticket(ticket),
        }
    )

    ticket_url = f"{settings.SITE_URL}{reverse('ticket_detail', kwargs={'ticket_id': ticket.id})}"
    
    subject = f"[New Ticket] Ticket #{ticket.id} Created"
    
    text_message = (
        f"A new ticket has been created.\n\n"
        f"- Ticket ID: {ticket.id}\n"
        f"- Title: {ticket.title}\n"
        f"- Priority: {ticket.priority}\n"
        f"- Category: {ticket.problem_category}\n"
        f"- Status: {ticket.status}\n"
        f"- Created At: {ticket.created_at}\n\n"
        f"Please review and assign it.\n\n"
        f"View ticket: {ticket_url}"
    )
    
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #d4edda; border-left: 4px solid #28a745; padding: 20px; margin-bottom: 20px;">
            <h2 style="color: #155724; margin-top: 0;">✨ New Ticket Created</h2>
        </div>
        
        <div style="background-color: #ffffff; padding: 20px; border: 1px solid #dee2e6; border-radius: 5px;">
            <table style="width: 100%;">
                <tr><td style="padding: 8px 0; font-weight: bold;">Ticket ID:</td><td>#{ticket.id}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Title:</td><td>{ticket.title}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Priority:</td><td>{ticket.priority}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Category:</td><td>{ticket.problem_category}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Status:</td><td>{ticket.status}</td></tr>
                <tr><td style="padding: 8px 0; font-weight: bold;">Created:</td><td>{ticket.created_at.strftime('%Y-%m-%d %H:%M')}</td></tr>
            </table>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{ticket_url}" 
               style="display: inline-block; background-color: #28a745; color: white; padding: 12px 30px; 
                      text-decoration: none; border-radius: 5px; font-weight: bold;">
                📋 View & Assign Ticket
            </a>
        </div>
    </body>
    </html>
    """

    recipients = list(
        User.objects.filter(groups__name__in=["Admin", "Director", "Manager", "Staff"])
        .exclude(email__isnull=True)
        .values_list("email", flat=True)
    )

    if not recipients:
        recipients = [settings.DEFAULT_FROM_EMAIL]

    sender = getattr(settings, "NEW_TICKET_SENDER", settings.DEFAULT_FROM_EMAIL)

    try:
        email = EmailMultiAlternatives(subject, text_message, sender, recipients)
        email.attach_alternative(html_message, "text/html")
        email.send()
        logger.info(f"✅ New ticket email sent for Ticket #{ticket.id}")
    except Exception as e:
        logger.error(f"❌ Failed to send new ticket email: {str(e)}")
        

def send_unassigned_ticket_notification(ticket):
    now = timezone.now()

    PRIORITY_THRESHOLDS = {
        'low': timedelta(hours=2),
        'medium': timedelta(hours=1.5),
        'high': timedelta(hours=1),
        'critical': timedelta(hours=0.5),
    }

    priority = (ticket.priority or "low").lower()
    threshold = PRIORITY_THRESHOLDS.get(priority, timedelta(minutes=8))

    if not ticket.assigned_to:
        elapsed = now - ticket.created_at

        if not ticket.last_unassigned_notification and elapsed >= threshold:
            _trigger_unassigned_alert(ticket, now)

        elif ticket.last_unassigned_notification and now >= ticket.last_unassigned_notification + threshold:
            _trigger_unassigned_alert(ticket, now)


"""def _trigger_unassigned_alert(ticket, now):
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

    recipients = get_escalation_recipients("General")
    sender = get_sender_for_level("General")

    try:
        send_mail(subject, message, sender, recipients)
        logger.info(f"Unassigned ticket email sent for Ticket #{ticket.id} to {recipients}")
    except Exception as e:
        logger.error(f"Failed to send unassigned ticket email for Ticket #{ticket.id}: {str(e)}")

    ticket.last_unassigned_notification = now
    ticket.save(update_fields=["last_unassigned_notification"])"""

def _trigger_unassigned_alert(ticket, now):
    """Send WebSocket + Email alert for unassigned ticket."""
    from django.urls import reverse
    from django.contrib.sites.shortcuts import get_current_site
    from django.core.mail import EmailMultiAlternatives
    
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "escalations",
        {
            "type": "unassigned_ticket_notification",
            "ticket": serialize_ticket(ticket),
        }
    )

    ticket_url = f"{settings.SITE_URL}{reverse('ticket_detail', kwargs={'ticket_id': ticket.id})}"
    
    subject = f"[Unassigned Ticket] Ticket #{ticket.id} ({ticket.priority.capitalize()} Priority)"
    
    text_message = (
        f"Ticket #{ticket.id} ({ticket.priority.capitalize()} priority) is still unassigned.\n\n"
        f"- Created At: {ticket.created_at}\n"
        f"- Current Status: {ticket.status}\n\n"
        f"Please assign this ticket as soon as possible.\n\n"
        f"View ticket: {ticket_url}"
    )
    
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #f8f9fa; border-left: 4px solid #dc3545; padding: 20px; margin-bottom: 20px;">
            <h2 style="color: #dc3545; margin-top: 0;">⚠️ Unassigned Ticket Alert</h2>
            <p style="font-size: 16px; margin-bottom: 10px;">
                <strong>Ticket #{ticket.id}</strong> ({ticket.priority.capitalize()} priority) is still unassigned.
            </p>
        </div>
        
        <div style="background-color: #ffffff; padding: 20px; border: 1px solid #dee2e6; border-radius: 5px; margin-bottom: 20px;">
            <h3 style="margin-top: 0; color: #495057;">Ticket Details</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; font-weight: bold; width: 40%;">Ticket ID:</td>
                    <td style="padding: 8px 0;">#{ticket.id}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold;">Title:</td>
                    <td style="padding: 8px 0;">{ticket.title}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold;">Priority:</td>
                    <td style="padding: 8px 0;">
                        <span style="background-color: {'#dc3545' if ticket.priority == 'critical' else '#ffc107' if ticket.priority == 'high' else '#17a2b8'}; 
                                     color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px;">
                            {ticket.priority.upper()}
                        </span>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold;">Status:</td>
                    <td style="padding: 8px 0;">{ticket.status}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold;">Created At:</td>
                    <td style="padding: 8px 0;">{ticket.created_at.strftime('%Y-%m-%d %H:%M')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; font-weight: bold;">Category:</td>
                    <td style="padding: 8px 0;">{ticket.problem_category if ticket.problem_category else 'N/A'}</td>
                </tr>
            </table>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{ticket_url}" 
               style="display: inline-block; background-color: #007bff; color: white; padding: 12px 30px; 
                      text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">
                📋 View Ticket Details
            </a>
        </div>
        
        <div style="background-color: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 5px; margin-top: 20px;">
            <p style="margin: 0; color: #856404;">
                <strong>⏰ Action Required:</strong> Please assign this ticket as soon as possible to ensure timely resolution.
            </p>
        </div>
        
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; font-size: 12px; color: #6c757d;">
            <p>This is an automated notification from the Blue River Technology Solutions Ticketing System.</p>
            <p>If you have any questions, please contact your system administrator.</p>
        </div>
    </body>
    </html>
    """

    recipients = get_escalation_recipients("General")
    sender = get_sender_for_level("General")

    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=sender,
            to=recipients
        )
        email.attach_alternative(html_message, "text/html")
        email.send()
        
        logger.info(f"Unassigned ticket email sent for Ticket #{ticket.id} to {recipients}")
    except Exception as e:
        logger.error(f"Failed to send unassigned ticket email for Ticket #{ticket.id}: {str(e)}")

    ticket.last_unassigned_notification = now
    ticket.save(update_fields=["last_unassigned_notification"])


def send_ticket_assignment_notification(ticket, assigned_user):
    """Notify user when a ticket has been assigned to them."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "escalations",
        {
            "type": "ticket_assignment_notification",
            "ticket": serialize_ticket(ticket),
            "assigned_to": assigned_user.username,
        }
    )

    subject = f"[Ticket Assignment] Ticket #{ticket.id} Assigned"
    message = (
        f"Ticket #{ticket.id} has been assigned to you.\n\n"
        f"- Title: {ticket.title}\n"
        f"- Priority: {ticket.priority}\n"
        f"- Category: {ticket.problem_category}\n"
        f"- Status: {ticket.status}\n\n"
        f"Please review and take action."
    )

    # Direct notification to the assigned user
    recipients = [assigned_user.email] if assigned_user.email else []

    # If user has no email, fall back to General tier
    if not recipients:
        recipients = get_escalation_recipients("General")

    sender = get_sender_for_level("General")

    try:
        send_mail(subject, message, sender, recipients)
        logger.info(f"✅ Assignment email sent for Ticket #{ticket.id} to {recipients}")
    except Exception as e:
        logger.error(f"❌ Failed to send assignment email for Ticket #{ticket.id}: {str(e)}")




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
    """Return recipient emails for a given escalation tier."""
    config = settings.ESCALATION_LEVEL_EMAILS.get(level)
    if config and "recipients" in config:
        return config["recipients"]
    return [settings.DEFAULT_FROM_EMAIL]

def get_sender_for_level(level):
    """Return the configured sender email for a tier, or fallback."""
    config = settings.ESCALATION_LEVEL_EMAILS.get(level)
    if config and "sender" in config:
        return config["sender"]
    return settings.DEFAULT_FROM_EMAIL

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
    sender = get_sender_for_level(to_level)

    try:
        send_mail(subject, message, sender, recipients)
        logger.info(f"📧 Escalation email sent for Ticket #{ticket.id} → {to_level} ({recipients})")
    except Exception as e:
        logger.error(f"❌ Failed to send escalation email for Ticket #{ticket.id}: {str(e)}")