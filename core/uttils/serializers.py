from django.utils.timezone import localtime

def serialize_ticket(t):
    if hasattr(t, "get_priority_display"):
        priority = t.get_priority_display()
    else:
        priority = t.priority or ""

    created_at = localtime(t.created_at).strftime("%Y-%m-%d %H:%M")
    escalated_at = (
        localtime(t.escalated_at).strftime("%Y-%m-%d %H:%M")
        if getattr(t, "escalated_at", None)
        else None
    )

    is_escalated = getattr(t, "is_escalated", False) or bool(escalated_at)

    # Decide notification type
    if is_escalated:
        notif_type = "escalated"
    elif not getattr(t, "assigned_to", None):  # no assignee
        notif_type = "unassigned"
    else:
        notif_type = "new"

    return {
        "id": t.id,
        "title": t.title,
        "priority": str(priority),
        "created_at": created_at,
        "escalated_at": escalated_at,
        "is_escalated": is_escalated,
        "notification_type": notif_type,
    }

def serialize_user_notification(un):
    ticket_data = serialize_ticket(un.ticket)
    # Inject per-user notification type
    ticket_data["notification_type"] = un.notification_type

    return {
        "notification_id": un.id,
        "is_read": un.is_read,
        "notification_type": un.notification_type,
        "ticket": ticket_data,
    }

