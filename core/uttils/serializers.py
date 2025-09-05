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

    return {
        "id": t.id,
        "title": t.title,
        "priority": str(priority),
        "created_at": created_at,
        "escalated_at": escalated_at,
        "is_escalated": is_escalated,
        "notification_type": "escalated" if is_escalated else "new",
    }
