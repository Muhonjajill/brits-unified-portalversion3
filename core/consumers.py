import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models.functions import Coalesce
from django.db.models import DateTimeField
from core.uttils.serializers import serialize_ticket
from core.models import Ticket, Customer, Terminal, Profile

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
        payload = [serialize_ticket(t) for t in tickets]
        total = await self._get_total_count()
        await self.send(text_data=json.dumps({
            "type": "notifications_list",
            "tickets": payload,   
            "count": total,       
        }))

    @database_sync_to_async
    def _get_latest_tickets(self):
        user = self.scope["user"]
        profile = getattr(user, "profile", None)

        qs = Ticket.objects.none()

        # Internal staff see all tickets
        if user.is_superuser or user.groups.filter(
            name__in=['Admin', 'Director', 'Manager', 'Staff']
        ).exists():
            qs = Ticket.objects.all()

        # Overseer: tickets for their customers
        elif Customer.objects.filter(overseer=user).exists():
            overseer_customers = Customer.objects.filter(overseer=user)
            qs = Ticket.objects.filter(customer__in=overseer_customers)

        # Custodian: tickets for their terminal
        elif profile and profile.terminal:
            if profile.terminal.custodian == user:
                qs = Ticket.objects.filter(terminal=profile.terminal)

        return list(qs.order_by("-created_at")[:5])


    @database_sync_to_async
    def _get_total_count(self):
        user = self.scope["user"]
        profile = getattr(user, "profile", None)

        qs = Ticket.objects.none()

        if user.is_superuser or user.groups.filter(
            name__in=['Admin', 'Director', 'Manager', 'Staff']
        ).exists():
            qs = Ticket.objects.all()

        elif Customer.objects.filter(overseer=user).exists():
            overseer_customers = Customer.objects.filter(overseer=user)
            qs = Ticket.objects.filter(customer__in=overseer_customers)

        elif profile and profile.terminal:
            if profile.terminal.custodian == user:
                qs = Ticket.objects.filter(terminal=profile.terminal)

        return qs.count()



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