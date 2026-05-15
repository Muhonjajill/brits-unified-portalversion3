from .imports import *
from .utility import export_tickets_to_excel

@login_required(login_url='login')
def tickets(request):
    query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    page_number = request.GET.get('page')
    tickets_qs = Ticket.objects.none()

    if request.user.is_authenticated:
        print(f"Authenticated user: {request.user.username}")
        profile = getattr(request.user, 'profile', None)

        if request.user.is_superuser or request.user.groups.filter(name__in=['Director', 'Manager']).exists():
            print("User has internal access (superuser/staff)")
            tickets_qs = Ticket.objects.all()

        elif request.user.groups.filter(name='Staff').exists():
            print(f"User is Staff - showing only assigned tickets for {request.user.username}")
            tickets_qs = Ticket.objects.filter(assigned_to=request.user)

        elif Customer.objects.filter(overseer=request.user).exists():
            customer = Customer.objects.filter(overseer=request.user).first()
            print(f"{request.user.username} is Overseer for {customer.name}")
            tickets_qs = Ticket.objects.filter(customer=customer)

        elif profile:
            if profile.terminal:
                print(f"{request.user.username} has terminal: {profile.terminal.branch_name}")
                customer = profile.terminal.customer

                # Ensure the custodian is linked to the correct terminal and customer
                if profile.terminal.custodian == request.user:
                    print(f"{request.user.username} is Custodian for terminal {profile.terminal.branch_name} under customer {customer.name}")
                    # Filter tickets by customer and terminal
                    tickets_qs = Ticket.objects.filter(customer=customer, terminal=profile.terminal)
                else:
                    print(f"{request.user.username} is not the custodian for terminal's customer")
            else:
                print(f"{request.user.username} has a profile but no terminal set")

        else:
            print(f"{request.user.username} has no profile or terminal set")

    # Apply search and status filters if applicable
    if query:
        tickets_qs = tickets_qs.filter(
            Q(id__icontains=query) |                          
            Q(title__icontains=query) |                       
            Q(description__icontains=query) |                 
            Q(terminal__branch_name__icontains=query) |       
            Q(status__icontains=query) |                      
            Q(assigned_to__username__icontains=query) |      
            Q(problem_category__name__icontains=query)        
        )


    if status_filter:
        if status_filter == 'escalated':
            tickets_qs = tickets_qs.filter(is_escalated=True)
        else:
            tickets_qs = tickets_qs.filter(status=status_filter)

    # Order by creation date
    tickets_qs = tickets_qs.order_by('-created_at')

    if request.GET.get('export') == 'excel':
        return export_tickets_to_excel(tickets_qs)

    # Pagination
    paginator = Paginator(tickets_qs, 10)
    page_obj = paginator.get_page(page_number)
    
    user_group = None
    if Customer.objects.filter(custodian=request.user).exists():
        user_group = "Custodian"
    elif Customer.objects.filter(overseer=request.user).exists():
        user_group = "Overseer"
    else:
        if request.user.groups.filter(name="Director").exists():
            user_group = "Director"
        elif request.user.groups.filter(name="Manager").exists():
            user_group = "Manager"
        elif request.user.groups.filter(name="Staff").exists():
            user_group = "Staff"
        else:
            user_group = "Customer"

    allowed_roles = ["Director", "Manager", "Staff", "Superuser"]

    return render(request, 'core/helpdesk/tickets.html', {
        'tickets': page_obj,
        'search_query': query,
        'status_filter': status_filter,
        'user_group': user_group,
        'allowed_roles':allowed_roles,
    })

def serialize_tickets(tickets):
    return [
        {
            "id": t.id,
            "title": t.title,
            "status": t.status,
            "priority": t.priority,
            "terminal_id": t.terminal_id if t.terminal else None,
            "created_by": t.created_by.username if t.created_by else None,
            "created_at": t.created_at.strftime("%Y-%m-%d %H:%M"),
            "assigned_to": t.assigned_to.username if t.assigned_to else None,
        }
        for t in tickets
    ]

def get_user_tickets_queryset(user):
    tickets_qs = Ticket.objects.none()
    profile = getattr(user, 'profile', None)

    if user.is_superuser or user.groups.filter(name__in=['Director', 'Manager']).exists():
        tickets_qs = Ticket.objects.all()

    elif user.groups.filter(name='Staff').exists():
        tickets_qs = Ticket.objects.filter(assigned_to=user)

    elif Customer.objects.filter(overseer=user).exists():
        customer = Customer.objects.filter(overseer=user).first()
        tickets_qs = Ticket.objects.filter(customer=customer)

    elif profile and profile.terminal:
        customer = profile.terminal.customer
        if profile.terminal.custodian == user:
            tickets_qs = Ticket.objects.filter(customer=customer, terminal=profile.terminal)

    return tickets_qs

def compute_time_data(qs):
    """
    Compute time-based aggregates from a filtered queryset.
    Ensures chart, KPI, and modal counts are always consistent.
    """
    now = timezone.now()
    start_of_week = now - timezone.timedelta(days=now.weekday())

    return {
        "day": qs.filter(created_at__date=now.date()).count(),
        "week": qs.filter(created_at__date__gte=start_of_week.date()).count(),
        "month": qs.filter(
            created_at__month=now.month,
            created_at__year=now.year
        ).count(),
        "year": qs.filter(created_at__year=now.year).count(),
    }


@login_required(login_url='login')
def api_tickets(request):
    # Base queryset (already scoped by user role/permissions)
    tickets = get_user_tickets_queryset(request.user).order_by('-created_at')
    now = timezone.now()

    # ----------------------------
    # Apply filters
    # ----------------------------
    if region := request.GET.get("region"):
        tickets = tickets.filter(terminal__zone__region__name=region)

    if customer := request.GET.get("customer"):
        tickets = tickets.filter(customer__name=customer)

    if terminal := request.GET.get("terminal"):
        tickets = tickets.filter(terminal_id=terminal)

    if status := request.GET.get("status"):
        tickets = tickets.filter(status=status)

    if priority := request.GET.get("priority"):
        tickets = tickets.filter(priority=priority)

    if category := request.GET.get("category"):
        tickets = tickets.filter(problem_category__name=category)

    # ----------------------------
    # Apply time period filter
    # ----------------------------
    if period := request.GET.get("period"):
        period = period.lower()

        if period in ("today", "day", "daily"):
            tickets = tickets.filter(created_at__date=now.date())

        elif period in ("week", "weekly"):
            start_of_week = now - timezone.timedelta(days=now.weekday())
            tickets = tickets.filter(created_at__date__gte=start_of_week.date())

        elif period in ("month", "monthly"):
            tickets = tickets.filter(
                created_at__month=now.month,
                created_at__year=now.year
            )

        elif period in ("year", "yearly"):
            tickets = tickets.filter(created_at__year=now.year)

    # ----------------------------
    # Time-based aggregates
    # ----------------------------
    time_data = compute_time_data(tickets)

    # ----------------------------
    # Response
    # ----------------------------
    return JsonResponse({
        "count": tickets.count(),
        "tickets": serialize_tickets(tickets),
        "time_data": time_data
    })


@login_required(login_url='login')
def create_ticket(request):
    user_group = None
    allowed_roles = []
    if request.user.groups.exists():
        user_group = request.user.groups.first().name
    if user_group == 'Admin':
        allowed_roles = ['Admin', 'Manager', 'Staff']
    elif user_group == 'Manager':
        allowed_roles = ['Manager', 'Staff']
    else:
        allowed_roles = ['Staff']

    is_manager_or_above = request.user.groups.filter(name__in=['Manager', 'Director']).exists()
    is_staff = request.user.groups.filter(name='Staff').exists()
    
    assignable_users = None
    if is_manager_or_above:
        assignable_users = User.objects.filter(groups__name__in=['Staff', 'Manager', 'Director']).distinct()
    elif is_staff:
        assignable_users = User.objects.filter(id=request.user.id)

    ticket_created = False 
    if request.method == 'POST':
        form = TicketForm(request.POST, user=request.user)
        if form.is_valid():
            ticket = form.save(commit=False)
            if ticket.terminal and not ticket.terminal.is_active:
                messages.error(
                    request,
                    f"Terminal '{ticket.terminal.cdm_name}' is disabled. "
                    "Please enable it before creating a ticket."
                )
                return redirect('create_ticket')
            ticket.created_by = request.user
            custom_date = form.cleaned_data.get('custom_created_at')
            if custom_date:
                ticket.created_at = custom_date
            if ticket.terminal:
                ticket.customer = ticket.terminal.customer
                ticket.region = ticket.terminal.region
            
            assigned_to_id = request.POST.get('assigned_to')
            if assigned_to_id and (is_manager_or_above or is_staff):
                if is_staff:
                    if int(assigned_to_id) == request.user.id:
                        ticket.assigned_to = request.user
                elif is_manager_or_above:
                    try:
                        assignee = User.objects.get(
                            id=assigned_to_id,
                            groups__name__in=['Staff', 'Manager', 'Director']
                        )
                        ticket.assigned_to = assignee
                    except User.DoesNotExist:
                        pass
            
            ticket.save()
            
            if ticket.assigned_to:
                subject = f"🎫 Ticket #{ticket.id} Assigned to You"
                text_content = (
                    f"Hello {ticket.assigned_to.get_full_name() or ticket.assigned_to.username},\n\n"
                    f"You have been assigned ticket #{ticket.id} - {ticket.title}.\n"
                    f"Please log in to the system to view and resolve it:\n"
                    f"{request.build_absolute_uri(reverse('ticket_detail', args=[ticket.id]))}\n\n"
                    f"Thank you."
                )
                html_content = render_to_string(
                    'email/ticket_detail_email.html',
                    {
                        'ticket': ticket,
                        'comments': [],
                        'ticket_url': request.build_absolute_uri(reverse('ticket_detail', args=[ticket.id]))
                    }
                )

                msg = EmailMultiAlternatives(
                    subject,
                    text_content,
                    settings.DEFAULT_FROM_EMAIL,
                    [ticket.assigned_to.email]
                )
                msg.attach_alternative(html_content, "text/html")

                logo_path = os.path.join(settings.BASE_DIR, 'static', 'icons', 'logo.png')
                if os.path.exists(logo_path):
                    with open(logo_path, 'rb') as f:
                        logo = MIMEImage(f.read())
                        logo.add_header('Content-ID', '<logo>')
                        logo.add_header('Content-Disposition', 'inline; filename="logo.png"')
                        msg.attach(logo)

                msg.send()
                
                ActivityLog.objects.create(
                    ticket=ticket,
                    action=f"Ticket assigned to {ticket.assigned_to.get_full_name() or ticket.assigned_to.username}",
                    user=request.user
                )
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "escalations",
                {
                    "type": "ticket_creation",
                    "ticket": ticket.id, 
                }
            )

            ticket_created = True
            if 'create_another' in request.POST:
                return render(
                    request,
                    'core/helpdesk/create_ticket.html',
                    {
                        'form': TicketForm(user=request.user),
                        'issue_mapping': json.dumps(build_issue_mapping()),
                        'user_group': user_group,
                        'allowed_roles': allowed_roles,
                        'ticket_created': True,
                        'is_manager': is_manager_or_above,
                        'is_staff': is_staff,
                        'assignable_users': assignable_users,
                    }
                )
            return redirect('tickets')
    else:
        terminal_id = request.GET.get('terminal_id')
        if terminal_id:
            form = TicketForm(user=request.user, terminal_id=terminal_id)
        else:
            form = TicketForm(user=request.user)
    cats = ProblemCategory.objects.all()
    js_mapping = {
        str(cat.pk): ISSUE_MAPPING.get(cat.name, [])
        for cat in cats
    }
    return render(request, 'core/helpdesk/create_ticket.html', {
        'form': form,
        'issue_mapping': json.dumps(js_mapping),
        'user_group': user_group,
        'allowed_roles': allowed_roles,
        'ticket_created': False,
        'is_manager': is_manager_or_above,
        'is_staff': is_staff,
        'assignable_users': assignable_users,
    })

from django.template.loader import render_to_string 
@login_required
def escalate_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Get the current escalation level
    level_order = [level[0] for level in Ticket.ESCALATION_LEVELS]
    
    # Find the current escalation level and the next level
    try:
        current_index = level_order.index(ticket.current_escalation_level) if ticket.current_escalation_level else -1
        next_level = level_order[current_index + 1]  # Next level
    except IndexError:
        messages.warning(request, "Already at the highest escalation level.")
        return redirect('ticket_detail', ticket_id=ticket.id)
    
    if request.method == 'POST':
        form = EscalationNoteForm(request.POST)
        if form.is_valid():
            print("Form is valid")
            note = form.cleaned_data['note']
            print(f"Escalation Note: {note}")  # Debugging line
            
            # Log the escalation to history
            EscalationHistory.objects.create(
                ticket=ticket,
                escalated_by=request.user,
                from_level=ticket.current_escalation_level,
                to_level=next_level,
                note=note
            )

            # Update ticket escalation
            ticket.current_escalation_level = next_level
            ticket.is_escalated = True
            ticket.escalated_at = timezone.now()
            ticket.escalated_by = request.user
            ticket.escalation_reason = note  
            ticket.save()

            # Create a visually appealing HTML email
            subject = f"Ticket #{ticket.id} Escalated to {ticket.current_escalation_level}"
            html_message = render_to_string('core/helpdesk/ticket_escalated.html', {
                'ticket': ticket,
                'note': note,
                'next_level': next_level
            })

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "escalations",
                {"type": "escalation.update"}  
            )
            
            ticket_url = (
                f"{settings.SITE_PROTOCOL}://{settings.SITE_DOMAIN}"
                f"{reverse('ticket_detail', args=[ticket.id])}"
            )

            send_mail(
                subject=f"Ticket #{ticket.id} Escalated to {ticket.current_escalation_level}",
                message=f"""
                Ticket ID: {ticket.id}
                Title: {ticket.title}
                Escalated By: {ticket.escalated_by}
                Escalation Level: {ticket.current_escalation_level}
                Reason: {ticket.escalation_reason}
                

                View Ticket: {ticket_url}

                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=get_email_for_level(next_level),  
                fail_silently=False,
            )

            messages.success(request, f"Ticket has been escalated to {next_level}.")
            return redirect('ticket_detail', ticket_id=ticket.id)
    else:
        print("There is a problem")
        form = EscalationNoteForm()

    return render(request, 'core/helpdesk/escalate_ticket.html', {
        'ticket': ticket,
        'form': form,
        'next_level': next_level
    })

@login_required
def ticket_activity_log(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    activity_logs = ActivityLog.objects.filter(ticket=ticket).order_by('-timestamp')

    user_group = None
    if Customer.objects.filter(custodian=request.user).exists():
        user_group = "Custodian"
    elif Customer.objects.filter(overseer=request.user).exists():
        user_group = "Overseer"
    else:
        if request.user.groups.filter(name="Director").exists():
            user_group = "Director"
        elif request.user.groups.filter(name="Manager").exists():
            user_group = "Manager"
        elif request.user.groups.filter(name="Staff").exists():
            user_group = "Staff"
        else:
            user_group = "Customer"

    allowed_roles = ["Director", "Manager", "Staff", "Superuser"]

    return render(request, 'core/helpdesk/ticket_activity_logs.html', {
        'ticket': ticket,
        'activity_logs': activity_logs,
        'user_group': user_group,
        'allowed_roles': allowed_roles
    })

@login_required
def clear_activity_logs(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    if request.method == "POST":
        ActivityLog.objects.filter(ticket=ticket).delete()
        messages.success(request, "All activity logs have been cleared.")
    
    return redirect('ticket_activity_log', ticket_id=ticket.id)


@login_required
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    comments = ticket.comments.order_by('-created_at')
    form = TicketEditForm(instance=ticket)
    comment_form = TicketCommentForm()

    # Check if the user is a manager or has a higher role (Staff, Manager, Director)
    is_manager_or_above = request.user.groups.filter(name__in=['Manager', 'Director']).exists()

    # Fetch all users from Staff, Manager, and Director for the dropdown (only for managers or higher)
    assignable_users = User.objects.filter(groups__name__in=['Staff', 'Manager', 'Director'])

    if request.method == 'POST':
        if 'add_comment' in request.POST:
            comment_form = TicketCommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.ticket = ticket
                comment.created_by = request.user
                comment.save()

                ticket.updated_by = request.user
                
                ticket.save(update_fields=['updated_at', 'updated_by'])

                return redirect('ticket_detail', ticket_id=ticket.id)

        elif 'edit_ticket' in request.POST:
            form = TicketEditForm(request.POST, instance=ticket)
            if form.is_valid():
                old_ticket = Ticket.objects.get(id=ticket.id)
                ticket = form.save(commit=False)
                ticket.updated_by = request.user

                changes = []
                watch_fields = [
                    'brts_unit', 'problem_category', 'title', 'terminal', 'description',
                    'customer', 'region', 'assigned_to', 'responsible', 'status',
                    'priority', 'is_escalated', 'current_escalation_level'
                ]

                for field in watch_fields:
                    old_value = getattr(old_ticket, field)
                    new_value = getattr(ticket, field)
                    if old_value != new_value:
                        changes.append((field, old_value, new_value))

                ticket.save()

                if changes:
                    change_summary = "\n".join([
                        f"• {field.replace('_', ' ').title()}: {old} → {new}"
                        for field, old, new in changes
                    ])

                    action = f"Ticket updated:\n{change_summary}"
                    ActivityLog.objects.create(
                        ticket=ticket,
                        action=action,
                        user=request.user
                    )

                return redirect('ticket_detail', ticket_id=ticket.id)

        elif 'assign_ticket' in request.POST and is_manager_or_above:
            staff_id = request.POST.get('assigned_to')
            if staff_id:
                staff_member = get_object_or_404(
                    User.objects.distinct(),
                    id=staff_id,
                    groups__name__in=['Staff', 'Manager', 'Director']
                )

                old_assigned_to = ticket.assigned_to
                ticket.assigned_to = staff_member
                ticket.updated_by = request.user
                ticket.save()

                if old_assigned_to != staff_member:
                    ActivityLog.objects.create(
                        ticket=ticket,
                        action=f"Ticket assigned: {old_assigned_to} → {staff_member}",
                        user=request.user
                    )

                subject = f"🎫 Ticket #{ticket.id} Assigned to You"
                text_content = f"Hello {staff_member.get_full_name() or staff_member.username},\n\nYou have been assigned ticket #{ticket.id} - {ticket.title}.\nPlease log in to the system to view and resolve it:\n{request.build_absolute_uri(reverse('ticket_detail', args=[ticket.id]))}\n\nThank you."
                html_content = render_to_string('email/ticket_detail_email.html', {'ticket': ticket, 'comments': comments, 'ticket_url': request.build_absolute_uri(reverse('ticket_detail', args=[ticket.id]))})

                msg = EmailMultiAlternatives(
                    subject,
                    text_content,
                    settings.DEFAULT_FROM_EMAIL,
                    [staff_member.email]
                )
                msg.attach_alternative(html_content, "text/html")

                logo_path = os.path.join(settings.BASE_DIR, 'static', 'icons', 'logo.png')
                if os.path.exists(logo_path):
                    with open(logo_path, 'rb') as f:
                        logo = MIMEImage(f.read())
                        logo.add_header('Content-ID', '<logo>')
                        logo.add_header('Content-Disposition', 'inline; filename="logo.png"')
                        msg.attach(logo)

                msg.send()

                # New Email to the ticket creator
                ticket_creator = ticket.created_by  # The user who created the ticket
                subject_creator = f"🎫 Ticket #{ticket.id} Assigned to {staff_member.get_full_name() or staff_member.username}"
                text_content_creator = (
                    f"Hello {ticket_creator.get_full_name() or ticket_creator.username},\n\n"
                    f"Ticket #{ticket.id} - {ticket.title} has been assigned to {staff_member.get_full_name() or staff_member.username}.\n\n"
                    f"Assigned To: {staff_member.get_full_name() or staff_member.username}\n"
                    f"Role: {', '.join([group.name for group in staff_member.groups.all()])}\n\n"
                    f"Please log in to the system to view and manage the ticket:\n"
                    f"{request.build_absolute_uri(reverse('ticket_detail', args=[ticket.id]))}\n\nThank you."
                )

                html_content_creator = render_to_string(
                    'email/ticket_creator_notification.html',  
                    {
                        'ticket': ticket,
                        'assignee': staff_member,
                        'ticket_url': request.build_absolute_uri(reverse('ticket_detail', args=[ticket.id]))
                    }
                )

                msg_creator = EmailMultiAlternatives(
                    subject_creator,
                    text_content_creator,
                    settings.DEFAULT_FROM_EMAIL,
                    [ticket_creator.email]
                )
                msg_creator.attach_alternative(html_content_creator, "text/html")

                logo_path_creator = os.path.join(settings.BASE_DIR, 'static', 'icons', 'logo.png')
                if os.path.exists(logo_path_creator):
                    with open(logo_path_creator, 'rb') as f:
                        logo_creator = MIMEImage(f.read())
                        logo_creator.add_header('Content-ID', '<logo>')
                        logo_creator.add_header('Content-Disposition', 'inline; filename="logo.png"')
                        msg_creator.attach(logo_creator)

                msg_creator.send()

                if old_assigned_to and old_assigned_to != staff_member:
                    ActivityLog.objects.create(
                        ticket=ticket,
                        action=f"Ticket assigned: {old_assigned_to} → {staff_member}",
                        user=request.user
                    )

                    recipients = [staff_member.email, ticket.created_by.email]
                    if old_assigned_to:  
                        recipients.append(old_assigned_to.email)

                    subject = f"🎫 Ticket #{ticket.id} Reassigned"
                    text_content = (
                        f"Hello,\n\n"
                        f"Ticket #{ticket.id} - {ticket.title} has been reassigned.\n\n"
                        f"Previous Assignee: {old_assigned_to.get_full_name() if old_assigned_to else 'None'}\n"
                        f"New Assignee: {staff_member.get_full_name() or staff_member.username}\n\n"
                        f"View Ticket: {request.build_absolute_uri(reverse('ticket_detail', args=[ticket.id]))}\n\n"
                        f"Thank you."
                    )

                    html_content = render_to_string(
                        'email/ticket_reassigned_notification.html',
                        {
                            'ticket': ticket,
                            'old_assignee': old_assigned_to,
                            'new_assignee': staff_member,
                            'ticket_url': request.build_absolute_uri(reverse('ticket_detail', args=[ticket.id]))
                        }
                    )

                    msg = EmailMultiAlternatives(
                        subject,
                        text_content,
                        settings.DEFAULT_FROM_EMAIL,
                        recipients
                    )
                    msg.attach_alternative(html_content, "text/html")

                    
                    logo_path = os.path.join(settings.BASE_DIR, 'static', 'icons', 'logo.png')
                    if os.path.exists(logo_path):
                        with open(logo_path, 'rb') as f:
                            logo = MIMEImage(f.read())
                            logo.add_header('Content-ID', '<logo>')
                            logo.add_header('Content-Disposition', 'inline; filename="logo.png"')
                            msg.attach(logo)

                    msg.send()

                #return redirect('ticket_detail', ticket_id=ticket.id)
                messages.success(request, f"Ticket #{ticket.id} successfully assigned to {staff_member.get_full_name()}")
                
                return redirect('tickets')

    activity_logs = ActivityLog.objects.filter(ticket=ticket).order_by('-timestamp')

    # Determine the user's group for displaying relevant permissions
    user_group = None
    if Customer.objects.filter(custodian=request.user).exists():
        user_group = "Custodian"
    elif Customer.objects.filter(overseer=request.user).exists():
        user_group = "Overseer"
    else:
        if request.user.groups.filter(name="Director").exists():
            user_group = "Director"
        elif request.user.groups.filter(name="Manager").exists():
            user_group = "Manager"
        elif request.user.groups.filter(name="Staff").exists():
            user_group = "Staff"
        else:
            user_group = "Customer"  

    context = {
        'ticket': ticket,
        'form': form,
        'comments': comments,
        'comment_form': comment_form,
        'is_manager': is_manager_or_above,
        'staff_users': assignable_users if is_manager_or_above else None,
        'activity_logs': activity_logs,
        'user_group': user_group,
        'allowed_roles': ['Director', 'Manager', 'Staff', 'Superuser'],
    }

    return render(request, 'core/helpdesk/ticket_detail.html', context)

@login_required
def resolve_ticket_view(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if ticket.assigned_to is None:
        messages.error(
            request,
            "This ticket must be assigned before it can be resolved."
        )
        return render(request, 'core/helpdesk/error.html')

    resolution = request.POST.get('resolution', '').strip()
    job_card_number = request.POST.get('job_card_number', '').strip()
    resolved_at = request.POST.get('resolved_at', '').strip()

    if not resolution:
        messages.error(request, "Resolution statement is required.")
        return render(request, 'core/helpdesk/error.html')
    
    is_remote_support = ticket.brts_unit and ticket.brts_unit.name == "Remote Support"
    if not is_remote_support and not job_card_number:
        messages.error(request, "Job Card Number is required for this unit.")
        return render(request, 'core/helpdesk/error.html')

    if is_director(request.user) or is_manager(request.user) or is_staff(request.user):
        if ticket.status != 'closed':
            if resolved_at:
                try:
                    resolved_at = datetime.strptime(resolved_at, "%Y-%m-%dT%H:%M")
                    resolved_at = timezone.make_aware(resolved_at)  
                except ValueError:
                    messages.error(request, "Invalid date format for 'Resolved At'. Please try again.")
                    return render(request, 'core/helpdesk/error.html')
            else:
                resolved_at = timezone.now()  

            if ticket.due_date and ticket.due_date.tzinfo is None:
                ticket.due_date = timezone.make_aware(ticket.due_date)

            ticket.resolution = resolution
            if not is_remote_support:
                ticket.job_card_number = job_card_number
            ticket.status = 'closed'
            ticket.resolved_by = request.user
            ticket.resolved_at = resolved_at
            ticket.save()

            if job_card_number:
                messages.success(request, f'Ticket resolved successfully! Job Card: {job_card_number}')
            else:
                messages.success(request, 'Ticket resolved successfully!')
            return redirect('tickets')
        else:
            messages.error(request, 'Ticket already resolved')
            return render(request, 'core/helpdesk/error.html')

    elif request.user.has_perm('can_resolve_ticket'):
        if ticket.status != 'closed':
            if resolved_at:
                try:
                    resolved_at = datetime.strptime(resolved_at, "%Y-%m-%dT%H:%M")
                    resolved_at = timezone.make_aware(resolved_at)  
                except ValueError:
                    messages.error(request, "Invalid date format for 'Resolved At'. Please try again.")
                    return render(request, 'core/helpdesk/error.html')
            else:
                resolved_at = timezone.now() 

            if ticket.due_date and ticket.due_date.tzinfo is None:
                ticket.due_date = timezone.make_aware(ticket.due_date)

            ticket.resolution = resolution
            if not is_remote_support:
                ticket.job_card_number = job_card_number
            ticket.status = 'closed'
            ticket.resolved_by = request.user
            ticket.resolved_at = resolved_at
            ticket.save()

            if job_card_number:
                messages.success(request, f'Ticket resolved successfully! Job Card: {job_card_number}')
            else:
                messages.success(request, 'Ticket resolved successfully!')
            return redirect('tickets')
        else:
            messages.error(request, 'Ticket already resolved!')
            return render(request, 'core/helpdesk/error.html')

    messages.error(request, 'You do not have permission to resolve this ticket.')
    return render(request, 'core/helpdesk/permission_denied.html')


@user_passes_test(is_director)
def delete_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    ticket.delete()
    messages.success(request, "Ticket deleted successfully.")
    return redirect('tickets')


@login_required(login_url='login')
def ticket_statuses(request):
    user = request.user
    is_custodian = user.groups.filter(name="Custodian").exists()
    is_overseer = user.groups.filter(name="Overseer").exists()
    is_customer = user.groups.filter(name="Customer").exists()

    user_group = None
    if Customer.objects.filter(custodian=request.user).exists():
        user_group = "Custodian"
    elif Customer.objects.filter(overseer=request.user).exists():
        user_group = "Overseer"
    else:
        if request.user.groups.filter(name="Director").exists():
            user_group = "Director"
        elif request.user.groups.filter(name="Manager").exists():
            user_group = "Manager"
        elif request.user.groups.filter(name="Staff").exists():
            user_group = "Staff"
        else:
            user_group = "Customer"

    allowed_roles = ["Director", "Manager", "Staff", "Superuser"]

    staff_performance = None
    date_range = request.GET.get('date_range', 'all')
    
    if user_group in allowed_roles or request.user.is_superuser:
        start_date = None
        now = timezone.now()
        
        if date_range == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == 'week':
            start_date = now - timedelta(days=now.weekday()) 
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == 'month':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif date_range == 'quarter':
            quarter_month = ((now.month - 1) // 3) * 3 + 1
            start_date = now.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        elif date_range == 'year':
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        staff_users = User.objects.filter(
            groups__name__in=['Director', 'Manager', 'Staff']
        ).distinct().order_by('first_name', 'last_name', 'username')
        
        performance_data = []
        for staff_user in staff_users:
            tickets_qs = Ticket.objects.filter(assigned_to=staff_user)
            
            if start_date:
                tickets_qs = tickets_qs.filter(created_at__gte=start_date)
            
            open_count = tickets_qs.filter(status='open').count()
            in_progress_count = tickets_qs.filter(status='in_progress').count()
            closed_count = tickets_qs.filter(status='closed').count()
            total_count = tickets_qs.count()
            
            user_groups = staff_user.groups.values_list('name', flat=True)
            if 'Director' in user_groups:
                role = 'Director'
            elif 'Manager' in user_groups:
                role = 'Manager'
            elif 'Staff' in user_groups:
                role = 'Staff'
            else:
                role = 'Unknown'
            
            performance_data.append({
                'staff': staff_user,
                'role': role,
                'open_count': open_count,
                'in_progress_count': in_progress_count,
                'closed_count': closed_count,
                'total_count': total_count,
            })
        
        page_number = request.GET.get('page', 1)
        paginator = Paginator(performance_data, 5)  
        staff_performance = paginator.get_page(page_number)

    return render(request, 'core/helpdesk/ticket_statuses.html', {
        "is_custodian": is_custodian,
        "is_overseer": is_overseer,
        "is_customer": is_customer,
        "user_group": user_group,
        "allowed_roles": allowed_roles,
        "staff_performance": staff_performance,
        "date_range": date_range,
    })


@login_required
def tickets_by_status(request, status):
    tickets_qs = Ticket.objects.filter(
        status__iexact=status.replace('-', '_')
    ).select_related('customer', 'terminal')

    user = request.user
    user_profile = getattr(user, 'profile', None) 

    # 1. Internal roles (Superusers and specific staff groups see all tickets)
    if user.is_superuser or user.groups.filter(name__in=['Director', 'Manager', 'Staff']).exists():
        print("User has internal access (superuser/staff) - viewing all tickets for this status.")

    elif Customer.objects.filter(overseer=user).exists():
        customer_overseen = Customer.objects.filter(overseer=user).first()
        if customer_overseen:
            print(f"{user.username} is Overseer for customer: {customer_overseen.name}")
            tickets_qs = tickets_qs.filter(customer=customer_overseen)
        else:
            tickets_qs = Ticket.objects.none()
            print(f"{user.username} is Overseer but no customer found (unexpected).")

    elif user_profile and user_profile.terminal:
        if user_profile.terminal.custodian == user:
            print(f"{user.username} is Custodian for terminal: {user_profile.terminal.branch_name}")
            tickets_qs = tickets_qs.filter(terminal=user_profile.terminal)
        else:
            tickets_qs = Ticket.objects.none()
            print(f"{user.username} has terminal in profile but is not its custodian. Returning no tickets.")
    else:
        tickets_qs = Ticket.objects.none()
        print(f"User {user.username} does not match any specific access role. Returning no tickets.")

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(tickets_qs, 10) 

    try:
        tickets = paginator.page(page)
    except PageNotAnInteger:
        tickets = paginator.page(1)
    except EmptyPage:
        tickets = paginator.page(paginator.num_pages)

    print(f"Final tickets count for {status} status: {tickets_qs.count()}")  

    user_group = None
    if Customer.objects.filter(custodian=request.user).exists():
        user_group = "Custodian"
    elif Customer.objects.filter(overseer=request.user).exists():
        user_group = "Overseer"
    else:
        if request.user.groups.filter(name="Director").exists():
            user_group = "Director"
        elif request.user.groups.filter(name="Manager").exists():
            user_group = "Manager"
        elif request.user.groups.filter(name="Staff").exists():
            user_group = "Staff"
        else:
            user_group = "Customer"

    allowed_roles = ["Director", "Manager", "Staff", "Superuser"]

    return render(request, 'core/helpdesk/ticket_by_status.html', {
        'user_group': user_group,
        'allowed_roles': allowed_roles,
        'status': status.title().replace('-', ' '),
        'tickets': tickets,
        'paginator': paginator
    })

@login_required(login_url='login')
def show_tickets(request, period):
    now = timezone.localtime(timezone.now())
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = day_start - timedelta(days=day_start.weekday())
    month_start = day_start.replace(day=1)
    year_start = day_start.replace(month=1, day=1)

    ticket_filter = Ticket.objects.none()
    profile = getattr(request.user, 'profile', None)

    PERIOD_MAP = {
        'today': 'daily',
        'this week': 'weekly',
        'this-week': 'weekly',
        'week': 'weekly',
        'this month': 'monthly',
        'this-month': 'monthly',
        'month': 'monthly',
        'this year': 'yearly',
        'this-year': 'yearly',
        'year': 'yearly',
    }

    period = PERIOD_MAP.get(period, period)


    # Role-based filtering
    if request.user.is_superuser or request.user.groups.filter(name__in=['Director', 'Manager', 'Staff']).exists():
        ticket_filter = Ticket.objects.all()
    else:
        customer = Customer.objects.filter(overseer=request.user).first()
        if customer:
            ticket_filter = Ticket.objects.filter(customer=customer)
        elif profile and profile.terminal:
            ticket_filter = Ticket.objects.filter(terminal=profile.terminal)

    # Filter tickets by period
    if period == 'daily':
        tickets = ticket_filter.filter(created_at__gte=day_start)
    elif period == 'weekly':
        tickets = ticket_filter.filter(created_at__gte=week_start)
    elif period == 'monthly':
        tickets = ticket_filter.filter(created_at__gte=month_start)
    elif period == 'yearly':
        tickets = ticket_filter.filter(created_at__gte=year_start)
    else:
        tickets = Ticket.objects.none()

    # Search filter
    search_query = request.GET.get('q', '')
    if search_query:
        tickets = tickets.filter(
            Q(title__icontains=search_query) |
            Q(customer__name__icontains=search_query) |
            Q(assigned_to__username__icontains=search_query)
        )

    # Pagination (10 per page)
    paginator = Paginator(tickets, 10)
    page_number = request.GET.get('page')
    tickets_page = paginator.get_page(page_number)

    # User group resolution
    if Customer.objects.filter(custodian=request.user).exists():
        user_group = "Custodian"
    elif Customer.objects.filter(overseer=request.user).exists():
        user_group = "Overseer"
    else:
        if request.user.groups.filter(name="Director").exists():
            user_group = "Director"
        elif request.user.groups.filter(name="Manager").exists():
            user_group = "Manager"
        elif request.user.groups.filter(name="Staff").exists():
            user_group = "Staff"
        else:
            user_group = "Customer"

    allowed_roles = ["Director", "Manager", "Staff", "Superuser"]

    return render(request, 'core/helpdesk/ticket_list.html', {
        'tickets': tickets_page,
        'period': period,
        'user_group': user_group,
        'allowed_roles': allowed_roles,
        'search_query': search_query,
    })

@login_required
def edit_comment(request, comment_id):
    comment = get_object_or_404(TicketComment, id=comment_id)

    if request.user != comment.created_by and not request.user.is_superuser:
        messages.error(request, "You don't have permission to edit this comment.")
        return redirect('ticket_detail', ticket_id=comment.ticket.id)

    if request.method == 'POST':
        form = TicketCommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            messages.success(request, "Comment updated successfully.")
            return redirect('ticket_detail', ticket_id=comment.ticket.id)
    else:
        form = TicketCommentForm(instance=comment)

    return render(request, 'core/helpdesk/edit_comment.html', {'form': form, 'comment': comment})


@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(TicketComment, id=comment_id)

    if request.user != comment.created_by and not request.user.is_superuser:
        messages.error(request, "You don't have permission to delete this comment.")
        return redirect('ticket_detail', ticket_id=comment.ticket.id)

    if request.method == 'POST':
        ticket_id = comment.ticket.id
        comment.delete()
        messages.success(request, "Comment deleted.")
        return redirect('ticket_detail', ticket_id=ticket_id)

@login_required(login_url='login')
def fetch_tickets(request, terminal_id):
    tickets = Ticket.objects.filter(terminal_id=terminal_id).values('id', 'title')
    
    if tickets:
        return JsonResponse({"success": True, "tickets": list(tickets)})
    else:
        return JsonResponse({"success": False, "message": "No tickets found."})

def get_email_for_level(level):
    config = settings.ESCALATION_LEVEL_EMAILS.get(level, {})
    return config.get("recipients", [])

def notify_group(level, ticket):
    email_recipient = get_email_for_level(level)  
    
    send_mail(
        f'Ticket #{ticket.id} has been escalated to {level}',
        f'The ticket with the issue "{ticket.title}" has been escalated to {level}.',
        settings.DEFAULT_FROM_EMAIL,
        [email_recipient],
        fail_silently=False
    )
