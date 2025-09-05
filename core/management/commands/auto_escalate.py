# core/management/commands/auto_escalate.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from core.utilss.escalation_constants import ESCALATION_FLOW, ESCALATION_TIME_LIMITS
from core.utilss.escalation_rules import escalate_ticket  # add import

class Command(BaseCommand):
    help = 'Auto-escalates tickets past escalation thresholds'

    def handle(self, *args, **kwargs):
        from core.models import Ticket, EscalationHistory  

        now = timezone.now()
        tickets = Ticket.objects.filter(status__in=['open', 'in_progress'])

        for ticket in tickets:
            if not ticket.priority:
                continue

            priority = ticket.priority.lower()
            if priority not in ESCALATION_TIME_LIMITS:
                continue

            threshold = timedelta(hours=ESCALATION_TIME_LIMITS[priority])

            # Optional: prevent constant re-escalation
            if ticket.escalated_at and (now - ticket.escalated_at < timedelta(hours=1)):
                continue

            if now - ticket.created_at > threshold:
                current = ticket.current_escalation_level or 'Tier 1'
                next_level = ESCALATION_FLOW.get(current)

                if next_level:
                    ticket.current_escalation_level = next_level
                    ticket.is_escalated = True
                    #ticket.status = 'escalated'
                    ticket.escalated_at = now
                    ticket.save()

                    EscalationHistory.objects.create(
                        ticket=ticket,
                        from_level=current,
                        to_level=next_level,
                        note='Auto-escalated by system'
                    )

                    self.stdout.write(f"✅ Escalated Ticket #{ticket.id} from {current} to {next_level}")