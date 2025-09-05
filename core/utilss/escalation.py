# core/utils/escalation.py

from datetime import timedelta, timezone
#from core.management.commands.auto_escalate import ESCALATION_TIME_LIMITS

from .escalation_rules import CATEGORY_TO_ESCALATION_TYPE, ESCALATION_MATRIX, TIER_MAPPING

from core.utilss.escalation_constants import ESCALATION_TIME_LIMITS, ESCALATION_FLOW
from core.utilss.escalation_rules import escalate_ticket  


def get_escalation_guidance(problem_category, priority):
    category = problem_category.strip().lower()
    severity = priority.strip().lower()

    escalation_type = CATEGORY_TO_ESCALATION_TYPE.get(category, 'technical outage')
    action = ESCALATION_MATRIX.get(escalation_type, {}).get(severity)
    tier = TIER_MAPPING.get(severity)

    return {
        "escalation_type": escalation_type,
        "escalation_tier": tier or "Unknown Tier",
        "escalation_action": action or "No defined escalation policy for this case."
    }



def handle(self, *args, **options):
    from core.models import Ticket
    now = timezone.now()
    for ticket in Ticket.objects.filter(status__in=['open', 'in_progress']):
        if not ticket.priority or not ticket.created_at:
            continue

        threshold_hours = ESCALATION_TIME_LIMITS.get(ticket.priority.lower())
        if not threshold_hours:
            continue

        time_since_created = now - ticket.created_at
        threshold = timedelta(hours=threshold_hours)

        if time_since_created > threshold:
            self.escalate_ticket(ticket)