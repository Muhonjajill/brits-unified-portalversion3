from .imports import *
from .auth_views import (
    send_role_assigned_email,
    send_role_removed_email,
    send_inhouse_user_email,
    send_overseer_email,
    send_custodian_email,
    send_user_updated_email,
)

@login_required(login_url='login')
def admin_dashboard(request):
    query = request.GET.get('q', '').strip()
    users_qs = User.objects.select_related('profile')
    customers_qs = Customer.objects.all()
    terminals_qs = Terminal.objects.select_related('custodian').all()

    if query:
        users_qs = users_qs.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)|
            Q(profile__phone_number__icontains=query)|
            Q(profile__id_number__icontains=query)
        )
        customers_qs = customers_qs.filter(Q(name__icontains=query))
        terminals_qs = terminals_qs.filter(Q(branch_name__icontains=query))

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'assign_overseer_or_custodian':
            customer_id = request.POST.get('customer_id')
            overseer_id = request.POST.get('overseer_id')

            customer = get_object_or_404(Customer, id=customer_id)

            if overseer_id:
                overseer = get_object_or_404(User, id=overseer_id)
                overseer.groups.add(Group.objects.get(name='Customer'))
                customer.overseer = overseer
                customer.save()
                messages.success(request, f"Overseer updated for {customer.name}.")
                send_role_assigned_email(overseer, 'Overseer', request, customer=customer)
            else:
                messages.warning(request, f"No overseer selected for {customer.name}.")

        elif action == 'assign_custodian':
            customer_id = request.POST.get('customer_id')
            terminal_id = request.POST.get('terminal_id')
            custodian_id = request.POST.get('custodian_id')

            customer = get_object_or_404(Customer, id=customer_id)
            terminal = get_object_or_404(Terminal, id=terminal_id)
            custodian = get_object_or_404(User, id=custodian_id)

            terminal.custodian = custodian
            terminal.save()

            custodian.groups.add(Group.objects.get(name='Customer'))

            profile, _ = Profile.objects.get_or_create(user=custodian)
            profile.terminal = terminal
            profile.customer = customer
            profile.save()

            terminal.refresh_from_db()
            custodian.refresh_from_db()
            if hasattr(custodian, 'profile'):
                custodian.profile.refresh_from_db()

            messages.success(request, f"Custodian {custodian.username} assigned to {terminal.branch_name}.")
            send_role_assigned_email(custodian, 'Custodian', request, customer=customer, terminal=terminal)

        elif action == 'update_role':
            user_id = request.POST.get('user_id')
            new_role = request.POST.get('new_role')

            if user_id and new_role:
                user = get_object_or_404(User, id=user_id)

                is_overseer = Customer.objects.filter(overseer=user).exists()
                is_custodian = Terminal.objects.filter(custodian=user).exists()
                is_customer = is_overseer or is_custodian

                restricted_roles = ['Director', 'Manager', 'Staff']
                if is_customer and new_role in restricted_roles:
                    messages.error(request, f"{user.username} is a Customer (overseer or custodian) and cannot be assigned the role '{new_role}'.")
                elif is_customer and new_role == 'Superuser':
                    messages.error(request, f"{user.username} is a Customer and cannot be made superuser.")
                else:
                    inhouse_roles = ['Director', 'Manager', 'Staff']
                    user.groups.remove(*Group.objects.filter(name__in=inhouse_roles))

                    group = Group.objects.get(name=new_role)
                    user.groups.add(group)

                    if new_role == 'Director':
                        assign_director_permissions(user)
                    elif new_role == 'Manager':
                        assign_manager_permissions(user)
                    elif new_role == 'Staff':
                        assign_staff_permissions(user)

                    user.save()
                    messages.success(request, f"{user.username}'s role updated to {new_role}.")
                    send_role_assigned_email(user, new_role, request)
            else:
                messages.error(request, "User ID or role missing in role update.")

        elif action == 'remove_assignment':
            target_type = request.POST.get('target_type')  
            customer_id = request.POST.get('customer_id')
            terminal_id = request.POST.get('terminal_id', None)
            user_id = request.POST.get('user_id') 

            if target_type == 'overseer':
                if not customer_id or not customer_id.isdigit():
                    messages.error(request, "Invalid customer ID.")
                else:
                    customer = get_object_or_404(Customer, id=customer_id)
                    removed_overseer = customer.overseer
                    if not removed_overseer:
                        messages.warning(request, "No overseer was assigned.")
                        return redirect('admin_dashboard')
                    customer.overseer = None
                    customer.save()
                    messages.success(request, f"Overseer removed from {customer.name}.")
                    if removed_overseer:
                        send_role_removed_email(removed_overseer, 'Overseer', request)

            elif target_type == 'custodian':
                if not terminal_id or not terminal_id.isdigit():
                    messages.error(request, "Invalid terminal ID.")
                else:
                    terminal = get_object_or_404(Terminal, id=terminal_id)
                    removed_custodian = terminal.custodian
                    if not removed_custodian:
                        messages.warning(request, "No custodian was assigned.")
                        return redirect('admin_dashboard')
                    terminal.custodian = None
                    terminal.save()
                    Profile.objects.filter(terminal=terminal).update(terminal=None, customer=None)
                    messages.success(request, f"Custodian removed from terminal {terminal.branch_name}.")
                    if removed_custodian:
                        send_role_removed_email(removed_custodian, 'Custodian', request)

            elif target_type == 'role':
                if not user_id or not user_id.isdigit():
                    messages.error(request, "Invalid user ID for role removal.")
                else:
                    user = get_object_or_404(User, id=user_id)
                    roles_to_remove = ['Director', 'Manager', 'Staff']
                    groups_to_remove = Group.objects.filter(name__in=roles_to_remove)
                    user.groups.remove(*groups_to_remove)
                    user.save()
                    messages.success(request, f"Roles removed from user {user.username}.")
                    send_role_removed_email(user, 'Role', request)

        elif action == 'delete_user':
            user_id = request.POST.get('user_id')
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                    username = user.username
                    user.delete()
                    messages.success(request, f"User {username} deleted successfully.")
                except User.DoesNotExist:
                    messages.error(request, "User not found.")
            else:
                messages.error(request, "No user ID provided for deletion.")

    # Access filtering logic
    tickets_qs = Ticket.objects.none()
    files_qs = File.objects.none()

    if request.user.is_superuser or request.user.groups.filter(name__in=['Director', 'Manager', 'Staff']).exists():
        tickets_qs = Ticket.objects.all()
        files_qs = File.objects.all()
    else:
        profile = getattr(request.user, 'profile', None)

        customer = Customer.objects.filter(overseer=request.user).first()
        if customer:
            tickets_qs = Ticket.objects.filter(customer=customer)
            files_qs = File.objects.filter(customer=customer) if hasattr(File, 'customer') else File.objects.none()

        elif profile and profile.terminal and profile.customer:
            tickets_qs = Ticket.objects.filter(customer=profile.customer, terminal=profile.terminal)
            files_qs = File.objects.filter(customer=profile.customer, terminal=profile.terminal) if hasattr(File, 'customer') else File.objects.none()

    # Separate in-house users from customer users
    inhouse_groups = ['Director', 'Manager', 'Staff']
    inhouse_users = users_qs.filter(
        Q(groups__name__in=inhouse_groups) | Q(is_superuser=True)
    ).distinct()
    
    # Get customer users by checking assignments
    overseer_ids = Customer.objects.filter(overseer__isnull=False).values_list('overseer_id', flat=True)
    custodian_ids = Terminal.objects.filter(custodian__isnull=False).values_list('custodian_id', flat=True).distinct()
    
    customer_user_ids = set(overseer_ids) | set(custodian_ids)
    customer_users = users_qs.filter(id__in=customer_user_ids)
    
    # Build customer assignments structure
    customer_assignments = []
    for customer in customers_qs.prefetch_related(
        Prefetch('terminal_set', queryset=Terminal.objects.select_related('custodian'))
    ):
        assignment = {
            'customer': customer,
            'overseer': customer.overseer,
            'custodians': []
        }
        
        for terminal in customer.terminal_set.all():
            if terminal.custodian:
                assignment['custodians'].append({
                    'user': terminal.custodian,
                    'terminal': terminal
                })
        
        customer_assignments.append(assignment)
    
    # Get all customers and terminals for dropdowns
    all_customers = Customer.objects.all()
    all_terminals = Terminal.objects.select_related('customer').all()
    
    # Build structured lists for "All Users Overview" section
    # Overseers list with customer info
    overseers = []
    for customer in Customer.objects.filter(overseer__isnull=False).select_related('overseer__profile'):
        overseers.append({
            'user': customer.overseer,
            'customer': customer
        })
    
    # Custodians list with terminal and customer info
    custodians = []
    for terminal in Terminal.objects.filter(custodian__isnull=False).select_related('custodian__profile', 'customer'):
        custodians.append({
            'user': terminal.custodian,
            'terminal': terminal,
            'customer': terminal.customer
        })
    
    # Users without any role assignment
    all_assigned_ids = customer_user_ids | set(inhouse_users.values_list('id', flat=True))
    users_without_roles = users_qs.exclude(id__in=all_assigned_ids)

    context = {
        'inhouse_users': inhouse_users,
        'customer_users': customer_users,
        'customer_assignments': customer_assignments,
        'customers': customers_qs,
        'all_customers': all_customers,
        'all_terminals': all_terminals,
        'terminals': terminals_qs,
        'total_users': User.objects.count(),
        'total_files': files_qs.count(),
        'open_tickets': tickets_qs.filter(status='open').count(),
        'overseers': overseers,  
        'custodians': custodians,  
        'users_without_roles': users_without_roles,  
    }

    return render(request, 'accounts/admin_dashboard.html', context)


@user_passes_test(is_director)
def create_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        first_name = request.POST.get('first_name') 
        last_name = request.POST.get('last_name') 
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        id_number = request.POST.get('id_number')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        user_type = request.POST.get('user_type')
        role = request.POST.get('role')
        
        customer_id = request.POST.get('customer_id')
        terminal_id = request.POST.get('terminal_id')

        # Validation
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('admin_dashboard')

        if not re.match(r"^(?:\+254|07)\d{8}$", phone):
            messages.error(request, 'Invalid phone number format. Please enter a valid Kenyan phone number.')
            return redirect('admin_dashboard')

        if len(id_number) < 8:
            messages.error(request, 'ID number must be at least 8 characters long.')
            return redirect('admin_dashboard')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('admin_dashboard')

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # Create/update profile
        profile, created = Profile.objects.get_or_create(user=user)
        profile.phone_number = phone
        profile.id_number = id_number

        # Handle role assignment based on user type
        if user_type == 'inhouse':
            if role == 'SuperAdmin':
                user.is_superuser = True
                user.is_staff = True
                user.save()
            else:
                group, _ = Group.objects.get_or_create(name=role)
                user.groups.add(group)
                
                if role == 'Director':
                    assign_director_permissions(user)
                elif role == 'Manager':
                    assign_manager_permissions(user)
                elif role == 'Staff':
                    assign_staff_permissions(user)
            
            profile.save()
            send_inhouse_user_email(request, user, password, role)
            messages.success(request, f"In-house user ({role}) created successfully.")
            
        elif user_type == 'customer':
            customer_group, _ = Group.objects.get_or_create(name='Customer')
            user.groups.add(customer_group)
            
            if role == 'Overseer':
                if customer_id:
                    customer = get_object_or_404(Customer, id=customer_id)
                    customer.overseer = user
                    customer.save()
                    profile.customer = customer
                    profile.save()
                    
                    send_overseer_email(request, user, password, customer)
                    messages.success(request, f"Overseer created and assigned to {customer.name}.")
                else:
                    messages.error(request, "Customer must be selected for Overseer role.")
                    user.delete()
                    return redirect('admin_dashboard')
                    
            elif role == 'Custodian':
                if customer_id and terminal_id:
                    customer = get_object_or_404(Customer, id=customer_id)
                    terminal = get_object_or_404(Terminal, id=terminal_id)
                    
                    terminal.custodian = user
                    terminal.save()
                    
                    profile.customer = customer
                    profile.terminal = terminal
                    profile.save()
                    
                    send_custodian_email(request, user, password, customer, terminal)
                    messages.success(request, f"Custodian created and assigned to {customer.name} - {terminal.branch_name}.")
                else:
                    messages.error(request, "Both Customer and Terminal must be selected for Custodian role.")
                    user.delete()
                    return redirect('admin_dashboard')

        return redirect('admin_dashboard')

    return render(request, 'accounts/admin_dashboard.html')


@login_required(login_url='login')
@user_passes_test(is_director)
def update_user(request):
    """Enhanced update view with email notifications"""
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        user = get_object_or_404(User, id=user_id)
        
        # Track what changed
        changes = []
        
        # Update basic info
        old_email = user.email
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        
        if old_email != user.email:
            changes.append(f"Email: {old_email} → {user.email}")
        
        # Update profile
        profile = user.profile
        old_phone = profile.phone_number
        old_id = profile.id_number
        profile.phone_number = request.POST.get('phone')
        profile.id_number = request.POST.get('id_number')
        
        if old_phone != profile.phone_number:
            changes.append(f"Phone: {old_phone} → {profile.phone_number}")
        if old_id != profile.id_number:
            changes.append(f"ID Number: {old_id} → {profile.id_number}")
        
        # Handle user type and role changes
        user_type = request.POST.get('user_type')
        new_role = request.POST.get('role')
        
        old_role = None
        if user.is_superuser:
            old_role = "SuperAdmin"
        elif user.groups.exists():
            old_role = user.groups.first().name
        
        if user_type == 'inhouse':
            # Remove any customer assignments
            Customer.objects.filter(overseer=user).update(overseer=None)
            Terminal.objects.filter(custodian=user).update(custodian=None)
            profile.customer = None
            profile.terminal = None
            
            # Remove customer group, add new role
            user.groups.clear()
            
            if new_role == 'SuperAdmin':
                user.is_superuser = True
                user.is_staff = True
            else:
                user.is_superuser = False
                group, _ = Group.objects.get_or_create(name=new_role)
                user.groups.add(group)
                
                if new_role == 'Director':
                    assign_director_permissions(user)
                elif new_role == 'Manager':
                    assign_manager_permissions(user)
                elif new_role == 'Staff':
                    assign_staff_permissions(user)
            
            if old_role != new_role:
                changes.append(f"Role: {old_role} → {new_role}")
                    
        elif user_type == 'customer':
            # Remove in-house groups
            user.groups.clear()
            user.is_superuser = False
            
            # Add customer group
            customer_group, _ = Group.objects.get_or_create(name='Customer')
            user.groups.add(customer_group)
            
            customer_id = request.POST.get('customer_id')
            terminal_id = request.POST.get('terminal_id')
            
            if new_role == 'Overseer':
                # Remove old assignments
                Customer.objects.filter(overseer=user).update(overseer=None)
                Terminal.objects.filter(custodian=user).update(custodian=None)
                
                # Assign new overseer
                customer = get_object_or_404(Customer, id=customer_id)
                customer.overseer = user
                customer.save()
                
                profile.customer = customer
                profile.terminal = None
                
                if old_role != 'Overseer':
                    changes.append(f"Role: {old_role} → Overseer for {customer.name}")
                
            elif new_role == 'Custodian':
                # Remove old assignments
                Customer.objects.filter(overseer=user).update(overseer=None)
                Terminal.objects.filter(custodian=user).update(custodian=None)
                
                # Assign new custodian
                customer = get_object_or_404(Customer, id=customer_id)
                terminal = get_object_or_404(Terminal, id=terminal_id)
                
                terminal.custodian = user
                terminal.save()
                
                profile.customer = customer
                profile.terminal = terminal
                
                if old_role != 'Custodian':
                    changes.append(f"Role: {old_role} → Custodian for {terminal.branch_name}")
        
        user.save()
        profile.save()
        
        # Send update notification email
        if changes:
            send_user_updated_email(request, user, changes, new_role, profile)
        
        messages.success(request, f"User {user.username} updated successfully.")
        return redirect('admin_dashboard')
    
    return redirect('admin_dashboard')

@login_required
def user_list_view(request):
    # Filter users based on groups excluding the 'Customer' group
    users = User.objects.exclude(groups__name='Customer').order_by('username')
    
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    can_view_logs = request.user.has_perm('core.view_fileaccesslog')
    
    return render(request, 'core/file_management/user_list.html', {'page_obj': page_obj, 'can_view_logs': can_view_logs})


@user_passes_test(is_staff)
def user_detail(request, user_id):
    user = get_object_or_404(User, id=user_id)
    return render(request, 'core/file_management/user_detail.html', {'user': user})

@user_passes_test(is_staff)
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.username = request.POST['username']
        user.email = request.POST['email']
        user.is_active = 'is_active' in request.POST
        user.save()
        messages.success(request, 'User updated successfully!')
        return redirect('user_list')
    return render(request, 'core/file_management/edit_user.html', {'user': user})

@permission_required('auth.delete_user', raise_exception=True)
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, 'User deleted successfully!')
    return redirect('user_list')

@login_required(login_url='login')
@user_passes_test(is_director)
def assign_role(request):
    """Assign role to unassigned users"""
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        user_type = request.POST.get('user_type')
        role = request.POST.get('role')
        
        user = get_object_or_404(User, id=user_id)
        profile = user.profile
        
        if user_type == 'inhouse':
            # Assign in-house role
            if role == 'SuperAdmin':
                user.is_superuser = True
                user.is_staff = True
            else:
                group, _ = Group.objects.get_or_create(name=role)
                user.groups.add(group)
                
                if role == 'Director':
                    assign_director_permissions(user)
                elif role == 'Manager':
                    assign_manager_permissions(user)
                elif role == 'Staff':
                    assign_staff_permissions(user)
            
            user.save()
            messages.success(request, f"{role} role assigned to {user.username}.")
            send_role_assigned_email(user, role, request)
            
        elif user_type == 'customer':
            customer_id = request.POST.get('customer_id')
            terminal_id = request.POST.get('terminal_id')
            
            customer_group, _ = Group.objects.get_or_create(name='Customer')
            user.groups.add(customer_group)
            
            if role == 'Overseer':
                customer = get_object_or_404(Customer, id=customer_id)
                customer.overseer = user
                customer.save()
                
                profile.customer = customer
                profile.save()
                
                messages.success(request, f"Overseer role assigned to {user.username} for {customer.name}.")
                send_role_assigned_email(user, 'Overseer', request, customer=customer)
                
            elif role == 'Custodian':
                customer = get_object_or_404(Customer, id=customer_id)
                terminal = get_object_or_404(Terminal, id=terminal_id)
                
                terminal.custodian = user
                terminal.save()
                
                profile.customer = customer
                profile.terminal = terminal
                profile.save()
                
                messages.success(request, f"Custodian role assigned to {user.username} for {terminal.branch_name}.")
                send_role_assigned_email(user, 'Custodian', request, customer=customer, terminal=terminal)
    
    return redirect('admin_dashboard')

@login_required(login_url='login')
def manage_file_categories(request):
    categories = FileCategory.objects.all()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create':
            name = request.POST.get('name')
            icon = request.POST.get('icon')
            if name and icon:  
                FileCategory.objects.create(name=name, icon=icon)
                messages.success(request, f'Category "{name}" created successfully.')
                return redirect('manage_file_categories')

        elif action == 'update':
            category_id = request.POST.get('category_id')
            new_name = request.POST.get('new_name')
            new_icon = request.POST.get('icon')
            category = get_object_or_404(FileCategory, id=category_id)
            
            # Preserve the existing icon if no new icon is selected
            category.name = new_name
            if new_icon:
                category.icon = new_icon  
            category.save()
            messages.success(request, f'Category "{new_name}" updated successfully.')
            return redirect('manage_file_categories')

        elif action == 'delete':
            category_id = request.POST.get('category_id')
            category = get_object_or_404(FileCategory, id=category_id)
            category.delete()
            messages.success(request, f'Category "{category.name}" deleted.')
            return redirect('manage_file_categories')

    can_view_logs = request.user.has_perm('core.view_fileaccesslog')

    return render(request, 'accounts/manage_file_categories.html', {
        'categories': categories,
        'can_view_logs': can_view_logs
    })

@login_required(login_url='login')
def system_users(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        role = request.POST.get('role')
        users = User.objects.all()
        if username and email and role:
            SystemUser.objects.create(username=username, email=email, role=role)
        return redirect('system_users')

    all_users = User.objects.all().order_by('id')
    # Add pagination: Show 10 users per page
    paginator = Paginator(all_users, 10)
    page_number = request.GET.get('page')
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

    return render(request, 'core/helpdesk/users.html',
                   {'page_obj': page_obj,
                    'user_group': user_group,
                    'allowed_roles': allowed_roles})

@user_passes_test(is_director)
def delete_system_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.user == user:
        messages.error(request, "You cannot delete your own account.")
    else:
        user.delete()
        messages.success(request, "User deleted successfully.")
    return redirect('system_users')