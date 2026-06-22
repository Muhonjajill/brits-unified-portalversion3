from .imports import *
from .utility import export_report_tickets_to_excel

@login_required
def problem_category(request):
    print(">>> problem_category view reached")
    query = request.GET.get('search', '')
    categories = ProblemCategory.objects.filter(name__icontains=query).order_by('name')
    print(f"Categories found: {categories.count()}")
    
    # Pagination setup
    paginator = Paginator(categories, 10)  
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
    
    return render(request, 'core/helpdesk/problem_category.html', {
        'page_obj': page_obj, 
        'search_query': query,
        'user_group': user_group,
        'allowed_roles': allowed_roles,
    })

@user_passes_test(is_director_or_manager)
def create_problem_category(request):
    if request.method == 'POST':
        print("POST received:", request.POST) 
        form = ProblemCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            print("Category saved!")

            # Redirect based on which button was clicked
            if 'create_another' in request.POST:
                return redirect('create_problem_category')
            return redirect('problem_category')  
        else:
            print("Form errors:", form.errors)
    else:
        form = ProblemCategoryForm()

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

    return render(request, 'core/helpdesk/create_problem_category.html',
                   {'form': form,
                    'user_group': user_group,
                    'allowed_roles': allowed_roles})

@user_passes_test(is_director)
def edit_problem_category(request, category_id):
    category = get_object_or_404(ProblemCategory, pk=category_id)
    if request.method == 'POST':
        form = ProblemCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect('problem_category')
    else:
        form = ProblemCategoryForm(instance=category)

    return render(request, 'core/helpdesk/edit_problem_category.html', {'form': form})

@user_passes_test(is_director)
def delete_problem_category(request, category_id):
    category = get_object_or_404(ProblemCategory, id=category_id)
    category.delete()
    messages.success(request, "Problem category deleted successfully.")
    return redirect('problem_category')

# Master Data Views
@login_required(login_url='login')
def customers(request):
    if request.method == "POST" and request.FILES.get("file"):
        csv_file = request.FILES["file"]
        decoded_file = csv_file.read().decode("utf-8").splitlines()
        reader = csv.DictReader(decoded_file)

        for row in reader:
            name = row.get("name", "").strip()
            if name: 
                Customer.objects.create(name=name)

        messages.success(request, "Customers uploaded successfully!")

    # Pagination setup
    all_customers = Customer.objects.exclude(name__exact="").exclude(name__isnull=True).order_by('id')
    paginator = Paginator(all_customers, 10)  
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

    return render(request, "core/helpdesk/customers.html",
                   {"customers": page_obj,
                    "user_group": user_group,
                    "allowed_roles": allowed_roles})

@login_required(login_url='login')
def customer_terminals(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    terminals_list = Terminal.objects.filter(customer=customer)
    
    # Pagination setup
    paginator = Paginator(terminals_list, 10)  
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

    return render(request, 'core/helpdesk/customer_terminals.html', {
        'customer': customer,
        'terminals': page_obj,
        'user_group': user_group,
        'allowed_roles': allowed_roles
    })

@login_required
def get_terminal_details(request, terminal_id):
    try:
        terminal = Terminal.objects.get(id=terminal_id)
        response_data = {
            'customer_id': terminal.customer.id if terminal.customer else None,
            'region_id': terminal.region.id if terminal.region else None,
        }
        return JsonResponse(response_data)
    except Terminal.DoesNotExist:
        return JsonResponse({'error': 'Terminal not found'}, status=404)

@user_passes_test(is_director_or_manager)
def create_customer(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if name:
            Customer.objects.create(name=name)
            messages.success(request, "Customer added successfully.")
            return redirect("customers")
        else:
            messages.error(request, "Customer name is required.")

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

    return render(request, "core/helpdesk/create_customer.html",
                   {'user_group': user_group,
                     'allowed_roles': allowed_roles})

@user_passes_test(is_director)
def delete_customer(request, id):
    customer = get_object_or_404(Customer, id=id)
    customer.delete()
    messages.success(request, "Customer deleted successfully.")
    return redirect('customers')

@login_required(login_url='login')
def regions(request):
    if request.method == 'POST':
        name = request.POST.get('region_name')
        if name:
            Region.objects.create(name=name)
            return redirect('regions')

    # Fetch all regions
    all_regions = Region.objects.all().order_by('id')

    # Pagination setup
    paginator = Paginator(all_regions, 10)  
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

    return render(request, 'core/helpdesk/regions.html',
                   {'regions': page_obj,
                    'user_group': user_group,
                    'allowed_roles': allowed_roles})


@login_required
@require_http_methods(["GET"])
def get_zones(request, region_id):
    """
    Return zones for a given region as JSON
    IMPORTANT: Only returns zones that belong to this specific region
    """
    try:
        region = Region.objects.get(id=region_id)
        
        zones = Zone.objects.filter(
            region_id=region_id
        ).prefetch_related('terminal_set')
        
        zones_data = []
        for zone in zones:
            terminal_count = Terminal.objects.filter(
                zone=zone,
                region=region
            ).count()
            
            if terminal_count > 0:
                zones_data.append({
                    'id': zone.id,
                    'name': zone.name,
                    'terminal_count': terminal_count
                })
        
        return JsonResponse({
            'zones': zones_data,
            'region_name': region.name
        })
        
    except Region.DoesNotExist:
        return JsonResponse({'error': f'Region with ID {region_id} not found'}, status=404)
    except Exception as e:
        print(f"Error in get_zones: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_terminals(request, zone_id):
    """
    Return terminals for a given zone as JSON
    """
    try:
        zone = Zone.objects.select_related('region').get(id=zone_id)
        
        terminals = Terminal.objects.filter(
            zone=zone
        ).select_related('customer', 'region')
        
        terminals_data = []
        for terminal in terminals:
            if terminal.region != zone.region:
                print(f"⚠️ Warning: Terminal {terminal.id} region mismatch!")
                terminal.region = zone.region
                terminal.save()
            
            terminals_data.append({
                'id': terminal.id,
                'branch_name': terminal.branch_name,
                'cdm_name': terminal.cdm_name,
                'serial_number': terminal.serial_number,
                'model': terminal.model,
                'is_active': terminal.is_active,
                'customer_name': terminal.customer.name if terminal.customer else None,
                'region_name': terminal.region.name if terminal.region else None,
                'zone_name': terminal.zone.name if terminal.zone else None,
            })
        
        return JsonResponse({
            'terminals': terminals_data,
            'zone_name': zone.name,
            'region_name': zone.region.name if zone.region else None
        })
        
    except Zone.DoesNotExist:
        return JsonResponse({'error': f'Zone with ID {zone_id} not found'}, status=404)
    except Exception as e:
        print(f"Error in get_terminals: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

@user_passes_test(is_director)
def delete_region(request, region_id):
    region = get_object_or_404(Region, id=region_id)
    region.delete()
    messages.success(request, "Region deleted successfully.")
    return redirect('regions')

@login_required(login_url='login')
def terminals(request):
    form = TerminalForm()
    upload_form = TerminalUploadForm()

    customers = Customer.objects.all()
    regions = Region.objects.all()
    zones = Zone.objects.all()

    if request.method == 'POST':
        if 'create' in request.POST or 'create_another' in request.POST:
            print("Form submitted")
            form = TerminalForm(request.POST)
            if form.is_valid():
                print("Form is valid")
                try:
                    terminal = form.save()

                    if terminal.zone and terminal.zone.region:
                        terminal.region = terminal.zone.region
                        terminal.save()

                    messages.success(request, "Terminal created successfully.")

                    if 'create_another' in request.POST:
                        return redirect('terminals')

                    return redirect('terminals')  
                except Exception as e:
                    messages.error(request, f"Error creating terminal: {e}")
                    print(f"Error creating terminal: {e}")
            else:
                print("Form is not valid")
                print("Form errors:", form.errors) 
        
        elif request.FILES.get('file'):
            upload_form = TerminalUploadForm(request.POST, request.FILES)
            if upload_form.is_valid():
                file = upload_form.cleaned_data['file']
                try:
                    ext = file.name.split('.')[-1].lower()
                    
                    if file.name.endswith('.csv'):
                        df = pd.read_csv(file)
                    else:
                        df = pd.read_excel(file)

                    # Process each row and create terminal objects
                    for _, row in df.iterrows():
                        try:
                            
                            customer_name = str(row["customer"]).strip()
                            branch_name = str(row["branch_name"]).strip()
                            cdm_name = str(row["cdm_name"]).strip()
                            serial_number = str(row["serial_number"]).strip()
                            region_name = str(row["region"]).strip()
                            model = str(row["model"]).strip()
                            zone_name = str(row["zone"]).strip()

                            customer = Customer.objects.get(name__iexact=customer_name)
                            region = Region.objects.get(name__iexact=region_name)
                            zone = Zone.objects.get(name__iexact=zone_name)

                            Terminal.objects.create(
                                customer=customer,
                                branch_name=branch_name,
                                cdm_name=cdm_name,
                                serial_number=serial_number,
                                region=region,
                                model=model,
                                zone=zone,
                            )

                            if terminal.zone and terminal.zone.region:
                                terminal.region = terminal.zone.region
                                terminal.save()

                        except Exception as e:
                            print(f"❌ Error on row: {row}")
                            print(f"Reason: {e}")
                            continue
                    messages.success(request, "Terminals imported successfully.")
                except Exception as e:
                    messages.error(request, f"Error importing file: {e}")
                return redirect('terminals')

    # GET request: Display the page with all terminals
    query = request.GET.get('q', '').strip()
    all_terminals = Terminal.objects.all().order_by('id') 
    if query:
        all_terminals = all_terminals.filter(
            Q(customer__name__icontains=query) |
            Q(branch_name__icontains=query) |
            Q(cdm_name__icontains=query) |
            Q(serial_number__icontains=query) |
            Q(region__name__icontains=query) |
            Q(model__icontains=query) |
            Q(zone__name__icontains=query)
        )
    paginator = Paginator(all_terminals, 10)  
    page_number = request.GET.get('page', 1)
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

    # Pass the required objects to the template
    return render(request, 'core/helpdesk/terminals.html', {
        'form': form,
        'upload_form': upload_form,
        'terminals': page_obj,
        'customers': customers,
        'regions': regions,
        'zones': zones,
        'user_group': user_group,
        'allowed_roles': allowed_roles,
        'search_query': query,
    })


@require_POST
def edit_terminal(request, terminal_id):
    terminal = get_object_or_404(Terminal, id=terminal_id)
    terminal.customer_id = request.POST.get('customer')
    terminal.branch_name = request.POST.get('branch_name')
    terminal.cdm_name = request.POST.get('cdm_name')
    terminal.serial_number = request.POST.get('serial_number')
    terminal.region_id = request.POST.get('region')
    terminal.model = request.POST.get('model')
    terminal.zone_id = request.POST.get('zone')

    if terminal.zone and terminal.zone.region:
        terminal.region = terminal.zone.region
    
    try:
        terminal.save()
        messages.success(request, "Terminal updated successfully.")
    except Exception as e:
        messages.error(request, f"Error updating terminal: {e}")
    
    return redirect('terminals')

@login_required
def disable_terminal(request, terminal_id):
    terminal = get_object_or_404(Terminal, id=terminal_id)
    if request.method == "POST":
        terminal.is_active = False  
        terminal.save()
        messages.success(request, f"Terminal {terminal.cdm_name} has been disabled.")
    return redirect('terminals')

@login_required
def enable_terminal(request, terminal_id):
    terminal = get_object_or_404(Terminal, id=terminal_id)
    if request.method == "POST":
        terminal.is_active = True
        terminal.save()
        messages.success(request, f"Terminal {terminal.cdm_name} has been enabled.")
    return redirect('terminals')


@user_passes_test(is_director)
def delete_terminal(request, terminal_id):
    terminal = get_object_or_404(Terminal, id=terminal_id)
    terminal.delete()
    messages.success(request, "Terminal removed successfully.")
    return redirect('terminals')

@login_required(login_url='login')
def units(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        if name and description:
            Unit.objects.create(name=name, description=description)
        return redirect('units')

    all_units = Unit.objects.all().order_by('id')
    
    paginator = Paginator(all_units, 10)
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

    return render(request, 'core/helpdesk/units.html',
                   {'page_obj': page_obj,
                    'user_group': user_group,
                    'allowed_roles': allowed_roles})

@user_passes_test(is_director)
def delete_unit(request, unit_id):
    unit = get_object_or_404(Unit, id=unit_id)
    unit.delete()
    messages.success(request, "Unit removed successfully.")
    return redirect('units')

@login_required(login_url='login')
def zones(request):
    if request.method == 'POST':
        name = request.POST.get('name')

        if name: 
            Zone.objects.create(name=name)
            messages.success(request, "Zone created successfully.")
            return redirect('zones')
        else:
            messages.error(request, "Name is required.")

    all_zones = Zone.objects.all().order_by('id')

    # Add pagination: Show 10 zones per page
    paginator = Paginator(all_zones, 10)
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

    return render(request, 'core/helpdesk/zones.html', {
        'page_obj': page_obj,
        'user_group': user_group,
        'allowed_roles': allowed_roles
    })

@user_passes_test(is_director)
def delete_zone(request, zone_id):
    zone = get_object_or_404(Zone, id=zone_id)
    zone.delete()
    messages.success(request, "Zone deleted successfully.")
    return redirect('zones') 

@login_required(login_url='login')
def version_controls(request):
    print("view reached") 
    form = VersionControlForm()

    if request.method == 'POST':
        if 'create' in request.POST or 'create_another' in request.POST:
            form = VersionControlForm(request.POST)
            if form.is_valid():
                print("form is valid")
                form.save()
                if 'create_another' in request.POST:
                    form = VersionControlForm()
                else:
                    return redirect('version_controls')
            else:
                print("Form is not valid")
    versions = VersionControl.objects.all().order_by('-created_at')

    # Handle AJAX filtering
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        terminal = request.GET.get('terminal')
        firmware = request.GET.get('firmware')
        app_version = request.GET.get('app_version')
        manufacturer = request.GET.get('manufacturer')

        if terminal and terminal != 'All':
            versions = versions.filter(terminal__id=terminal)
        if manufacturer and manufacturer != 'All':
            versions = versions.filter(manufacturer=manufacturer)
        

        return render(request, 'core/helpdesk/partials/version_table.html', {
            'versions': versions
        })

    # Paginate the full list
    paginator = Paginator(versions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Terminal filter options
    terminals = VersionControl.objects.select_related('terminal').values(
        'terminal__branch_name', 'terminal__id'
    ).distinct()

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

    context = {
        'form': form,
        'page_obj': page_obj,
        'versions': page_obj,  
        'terminals': terminals,
        'manufacturers': VersionControl.objects.values_list('manufacturer', flat=True).distinct(),
        'user_group': user_group,
        'allowed_roles': allowed_roles
        #'firmwares': VersionControl.objects.values_list('firmware', flat=True).distinct(),
        #'app_versions': VersionControl.objects.values_list('app_version', flat=True).distinct(),
    }
    return render(request, 'core/helpdesk/version_control.html', context)

@login_required(login_url='login')
def version_detail(request, pk):
    version = get_object_or_404(VersionControl, pk=pk)
    comments = version.comments.all().order_by('-created')  # Latest first

    if request.method == 'POST':
        comment_text = request.POST.get('comment')
        if comment_text:
            VersionComment.objects.create(version=version, text=comment_text)
        return redirect('version_detail', pk=pk)

    return render(request, 'core/helpdesk/version_detail.html', {
        'version': version,
        'comments': comments,
        
    })

@login_required(login_url='login')
def edit_version(request, pk):
    version = get_object_or_404(VersionControl, pk=pk)
    if request.method == 'POST':
        form = VersionControlForm(request.POST, instance=version)
        if form.is_valid():
            form.save()
            return redirect('version_detail', pk=pk)
    else:
        form = VersionControlForm(instance=version)

    return render(request, 'core/helpdesk/edit_version.html', {'form': form, 'version': version})

@user_passes_test(is_director)
def delete_version(request, pk):
    version = get_object_or_404(VersionControl, pk=pk)
    version.delete()
    return redirect('version_controls') 


@login_required(login_url='login')
def reports(request):
    user_group = None
    customers = Customer.objects.all()
    terminals = Terminal.objects.all()

    # Correct way to get a single terminal for the custodian
    terminals = Terminal.objects.filter(custodian=request.user)  # Still returns a QuerySet
    if terminals.exists():
        terminal = terminals.first() 
        user_group = "Custodian"
        terminal = Terminal.objects.filter(custodian=request.user)
        customers = Customer.objects.filter(
            id__in=terminal.values_list('customer_id', flat=True)
        ) # Get the first terminal if it exists
    # Custodian logic
    #if Terminal.objects.filter(custodian=request.user).exists():
        
    elif Customer.objects.filter(overseer=request.user).exists():
        user_group = "Overseer"
        assigned_customers = Customer.objects.filter(overseer=request.user)
        customers = assigned_customers  # Only customers assigned to the overseer

    # Base ticket query
    tickets = Ticket.objects.prefetch_related('comments').all().order_by('-created_at')

    # Apply user‐level filtering
    if user_group == "Custodian":
        tickets = tickets.filter(terminal__in=terminals)
    elif user_group == "Overseer":
        tickets = tickets.filter(customer__in=customers)

    customer = request.GET.get('customer')
    terminal_name = request.GET.get("terminal_name")
    region = request.GET.get('region')
    category = request.GET.get('category')

    filter_by_customer = False
    filter_by_terminal = False

    if customer and customer != 'All' and customer != "None":
        tickets = tickets.filter(customer_id=customer)
        filter_by_customer = True

    if terminal_name:
        tickets = tickets.filter(terminal__branch_name__icontains=terminal_name)
        filter_by_terminal = True

    if region and region != 'All' and region != "None":
        tickets = tickets.filter(region_id=region)

    if category and category != 'All' and category != "None":
        tickets = tickets.filter(problem_category_id=category)

    # Date filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date:
        tickets = tickets.filter(created_at__date__gte=parse_date(start_date))
    if end_date:
        tickets = tickets.filter(created_at__date__lte=parse_date(end_date))

    # Export to Excel logic
    if request.GET.get('download') == 'excel':
        customer_name = Customer.objects.get(id=customer).name if customer and customer not in ['All', 'None'] else None
        terminal_filter = terminal_name if terminal_name else None

        return export_report_tickets_to_excel(
            tickets,
            customer_name=customer_name,
            terminal_name=terminal_filter,
            start_date=start_date,
            end_date=end_date
        )

    # Pagination
    paginator = Paginator(tickets, 10)
    page = request.GET.get('page')

    try:
        tickets_page = paginator.page(page)
    except PageNotAnInteger:
        tickets_page = paginator.page(1)
    except EmptyPage:
        tickets_page = paginator.page(paginator.num_pages)

    selected_customer = None
    if user_group == "Custodian" and customers.exists():
        selected_customer = customers.first()
    elif user_group == "Overseer" and customers.exists():
        selected_customer = customers.first()

    
    users_group = None
    if Customer.objects.filter(custodian=request.user).exists():
        users_group = "Custodian"
    elif Customer.objects.filter(overseer=request.user).exists():
        users_group = "Overseer"
    else:
        if request.user.groups.filter(name="Director").exists():
            users_group = "Director"
        elif request.user.groups.filter(name="Manager").exists():
            users_group = "Manager"
        elif request.user.groups.filter(name="Staff").exists():
            users_group = "Staff"
        else:
            users_group = "Customer"

    allowed_roles = ["Director", "Manager", "Staff", "Superuser"]
    

    # Context to be passed to the template
    context = {
        'tickets': tickets_page,
        'page_obj': tickets_page,
        'customers': customers,
        "selected_customer": selected_customer,
        'terminals': terminals,
        'regions': Region.objects.all(),
        'categories': ProblemCategory.objects.all(),
        'filter_by_customer': filter_by_customer,
        'filter_by_terminal': filter_by_terminal,
        'user_group': user_group,  
        'users_group':users_group,
        'allowed_roles':allowed_roles
    }

    return render(request, 'core/helpdesk/reports.html', context)

