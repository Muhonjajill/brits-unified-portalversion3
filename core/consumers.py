import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models.functions import Coalesce
from django.db.models import DateTimeField
from core.uttils.serializers import serialize_ticket, serialize_user_notification
from core.models import Ticket, Customer, Terminal, Profile, UserNotification
import logging

logger = logging.getLogger(__name__)


class EscalationConsumer(AsyncWebsocketConsumer):
    group_name = "escalations"

    async def connect(self):
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_latest()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_latest(self):
        tickets = await self._get_latest_tickets()
        total = await self._get_total_count()
        await self.send(text_data=json.dumps({
            "type": "notifications_list",
            "tickets": tickets,   
            "count": total,
        }))

    @database_sync_to_async
    def _get_latest_tickets(self):
        user = self.scope["user"]
        profile = getattr(user, "profile", None)

        qs = UserNotification.objects.none()

        # All queries MUST be scoped to this user
        if user.is_superuser or user.groups.filter(
            name__in=['Admin', 'Director', 'Manager', 'Staff']
        ).exists():
            qs = UserNotification.objects.filter(user=user, is_read=False)

        elif Customer.objects.filter(overseer=user).exists():
            overseer_customers = Customer.objects.filter(overseer=user)
            qs = UserNotification.objects.filter(
                ticket__customer__in=overseer_customers,
                user=user,
                is_read=False
            )

        elif profile and profile.terminal and profile.terminal.custodian == user:
            qs = UserNotification.objects.filter(
                ticket__terminal=profile.terminal,
                user=user,
                is_read=False
            )

        qs_unread = qs.select_related("ticket").order_by("-ticket__created_at")

        # Deduplicate by ticket_id (keep newest)
        seen = set()
        top5 = []
        for un in qs_unread:
            if un.ticket_id not in seen:
                seen.add(un.ticket_id)
                top5.append(un)
            if len(top5) == 5:
                break

        logger.info("Notifications for %s: %s", self.scope["user"], list(qs.values("user_id", "ticket_id")))
        return [serialize_user_notification(un) for un in top5]


    @database_sync_to_async
    def _get_total_count(self):
        user = self.scope["user"]
        profile = getattr(user, "profile", None)

        qs = UserNotification.objects.none()

        if user.is_superuser or user.groups.filter(
            name__in=['Admin', 'Director', 'Manager', 'Staff']
        ).exists():
            qs = UserNotification.objects.filter(user=user, is_read=False)
        elif Customer.objects.filter(overseer=user).exists():
            overseer_customers = Customer.objects.filter(overseer=user)
            qs = UserNotification.objects.filter(
                ticket__customer__in=overseer_customers,
                user=user,
                is_read=False
            )
        elif profile and profile.terminal and profile.terminal.custodian == user:
            qs = UserNotification.objects.filter(
                ticket__terminal=profile.terminal,
                user=user,
                is_read=False
            )

        # Return distinct ticket count — matches the UI list
        return qs.values("ticket_id").distinct().count()


    async def escalation_update(self, event):
        # On escalation, refresh the list
        await self.send_latest()

    async def ticket_creation(self, event):
            t = event["ticket"]
            if isinstance(t, dict):
                payload = t
            else:
                try:
                    ticket = await database_sync_to_async(Ticket.objects.get)(id=t)
                    payload = serialize_ticket(ticket)
                except ObjectDoesNotExist:
                    return
            await self.send(text_data=json.dumps({
                "type": "ticket_creation",
                "ticket": payload,
            }))

    async def escalation_message(self, event):
        # Optional toast-like messages
        msg = event.get("message")
        await self.send(text_data=json.dumps({
            "type": "escalation_message",
            "message": msg if isinstance(msg, str) else json.dumps(msg),
        }))

        await self.send_latest()


    async def unassigned_ticket_notification(self, event):
        """Send unassigned ticket notification only if relevant for this user."""
        user = self.scope["user"]
        profile = getattr(user, "profile", None)

        ticket = event.get("ticket")
        if not ticket:
            return

        # Ensure we have a Ticket object
        if isinstance(ticket, dict):
            ticket = await database_sync_to_async(Ticket.objects.get)(id=ticket.get("id"))

        send_to_user = await self._should_send_unassigned(user, profile, ticket)

        if send_to_user:
            ticket_data = serialize_ticket(ticket)
            await self.send(text_data=json.dumps({
                "type": "unassigned_ticket_notification",
                "ticket": ticket_data
            }))

    @database_sync_to_async
    def _should_send_unassigned(self, user, profile, ticket):
        """Check if user should see this unassigned ticket (runs in threadpool)."""
        # Staff/admins: see all
        if user.is_superuser or user.groups.filter(
            name__in=["Admin", "Director", "Manager", "Staff"]
        ).exists():
            return True

        # Overseer: tickets for their customers
        if ticket.customer and ticket.customer.overseer_id == user.id:
            return True

        # Custodian: tickets for their assigned terminal
        if profile and profile.terminal and ticket.terminal_id == profile.terminal_id:
            if profile.terminal.custodian_id == user.id:
                return True

        return False

    async def new_ticket_notification(self, event):
        await self.send_json({
            "type": "new_ticket_notification",
            "ticket": event["ticket"],
        })
