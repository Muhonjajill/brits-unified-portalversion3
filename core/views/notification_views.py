from .imports import *

@login_required
def get_notifications(request):
    profile = getattr(request.user, "profile", None)
    qs = UserNotification.objects.none()

    # Internal staff: only notifications for this user
    if request.user.is_superuser or request.user.groups.filter(
        name__in=['Admin','Director','Manager','Staff']
    ).exists():
        qs = UserNotification.objects.filter(user=request.user)

    # Overseer: notifications for their customers (but still only this user)
    elif Customer.objects.filter(overseer=request.user).exists():
        overseer_customers = Customer.objects.filter(overseer=request.user)
        qs = UserNotification.objects.filter(
            ticket__customer__in=overseer_customers,
            user=request.user
        )

    # Custodian: notifications for the terminal they are assigned to (again only this user)
    elif profile and profile.terminal:
        custodian_terminal = profile.terminal
        if custodian_terminal.custodian == request.user:
            qs = UserNotification.objects.filter(
                ticket__terminal=custodian_terminal,
                user=request.user
            )

    # unread queryset (ordered most recent ticket first)
    qs_unread = qs.filter(is_read=False) \
                  .select_related("ticket", "ticket__customer", "ticket__terminal") \
                  .order_by("-ticket__created_at")

    # total should be distinct tickets count (so the badge matches the visible items)
    total_unread = qs_unread.values("ticket_id").distinct().count()

    # build top5 deduped by ticket_id (DB-agnostic)
    seen = set()
    top5 = []
    for un in qs_unread:
        if un.ticket_id not in seen:
            seen.add(un.ticket_id)
            top5.append(un)
        if len(top5) == 5:
            break

    if not top5:
        return JsonResponse({
            "tickets": [],
            "count": total_unread,
            "message": "No notifications available for your role or assignment."
        })

    payload = [serialize_user_notification(un) for un in top5]

    return JsonResponse({
        "tickets": payload,
        "count": total_unread,
    })

logger = logging.getLogger(__name__)

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    # Fetch notification by its unique id for the logged-in user
    notif = UserNotification.objects.filter(
        user=request.user,
        id=notification_id
    ).first()

    if notif:
        if not notif.is_read:
            notif.is_read = True
            notif.save(update_fields=["is_read"])

        logger.info(
            "Notification marked read: user=%s notification_id=%s ticket=%s",
            request.user, notification_id, notif.ticket_id
        )

        # Respond with notification_id so frontend can remove the exact item
        return JsonResponse({"success": True, "notification_id": notification_id})

    logger.error(
        "No UserNotification found for user=%s notification_id=%s",
        request.user, notification_id
    )
    return JsonResponse({"success": False, "info": "Notification not found"})


@login_required
@require_POST
def mark_all_notifications_read(request):
    """Mark all unread notifications for the current user as read"""
    profile = getattr(request.user, "profile", None)
    qs = UserNotification.objects.none()

    # Internal staff: only notifications for this user
    if request.user.is_superuser or request.user.groups.filter(
        name__in=['Admin','Director','Manager','Staff']
    ).exists():
        qs = UserNotification.objects.filter(user=request.user, is_read=False)

    # Overseer: notifications for their customers
    elif Customer.objects.filter(overseer=request.user).exists():
        overseer_customers = Customer.objects.filter(overseer=request.user)
        qs = UserNotification.objects.filter(
            ticket__customer__in=overseer_customers,
            user=request.user,
            is_read=False
        )

    # Custodian: notifications for the terminal
    elif profile and profile.terminal:
        custodian_terminal = profile.terminal
        if custodian_terminal.custodian == request.user:
            qs = UserNotification.objects.filter(
                ticket__terminal=custodian_terminal,
                user=request.user,
                is_read=False
            )

    # Mark all as read
    count = qs.update(is_read=True)

    logger.info(
        "Marked %d notifications as read for user=%s",
        count, request.user
    )

    return JsonResponse({
        "success": True,
        "count": count,
        "message": f"{count} notification(s) marked as read"
    })

@login_required
def get_escalated_tickets(request):
    # Filter tickets that are escalated
    escalated_tickets = Ticket.objects.filter(is_escalated=True).order_by('-escalated_at')

    # Return JSON for AJAX
    data = {
        "count": escalated_tickets.count(),
        "tickets": [
            {
                "id": t.id,
                "title": t.title,
                "escalated_at": t.escalated_at.strftime('%Y-%m-%d %H:%M'),
                "level": t.current_escalation_level
            }
            for t in escalated_tickets
        ]
    }
    return JsonResponse(data)

@login_required
def escalated_tickets_page(request):
    profile = getattr(request.user, 'profile', None)
    tickets_qs = Ticket.objects.filter(is_escalated=True)  

    if request.user.is_superuser or request.user.groups.filter(
        name__in=['Director', 'Manager', 'Staff']
    ).exists():
        pass 

    elif Customer.objects.filter(overseer=request.user).exists():
        overseer_customers = Customer.objects.filter(overseer=request.user)
        tickets_qs = tickets_qs.filter(customer__in=overseer_customers)

    elif profile and profile.terminal:
        if profile.terminal.custodian == request.user:
            tickets_qs = tickets_qs.filter(terminal=profile.terminal)
        else:
            tickets_qs = Ticket.objects.none() 

    else:
        tickets_qs = Ticket.objects.none() 

    tickets_qs = tickets_qs.order_by('-escalated_at')

    # Pagination
    paginator = Paginator(tickets_qs, 10)  
    page_number = request.GET.get('page', 1)
    
    try:
        tickets = paginator.page(page_number)
    except PageNotAnInteger:
        tickets = paginator.page(1)
    except EmptyPage:
        tickets = paginator.page(paginator.num_pages)

    return render(request, "core/helpdesk/escalated_list.html", {
        #"tickets": tickets_qs,
        "tickets": tickets,
        "total_count": tickets_qs.count(),
    })