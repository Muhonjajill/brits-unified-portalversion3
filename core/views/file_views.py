from .imports import *

@login_required
def file_management_dashboard(request):
    user = request.user
    
    if user.is_superuser:
        files = File.objects.filter(is_deleted=False)
    else:
        files = File.objects.filter(
            is_deleted=False
        ).filter(
            Q(access_level='public') |
            Q(access_level='restricted', authorized_users=user) |
            Q(access_level='confidential', uploaded_by=user)
        )
    
    ext_counter = Counter()
    for f in files:
        if f.file_exists():
            ext = f.get_file_extension()
            if ext:
                ext_counter[ext] += 1

    file_types = [
        {"type": "PDF Documents", "ext": ".pdf", "icon": "pdf", "count": ext_counter.get(".pdf", 0)},
        {"type": "Word Documents", "ext": ".docx", "icon": "docx", "count": ext_counter.get(".docx", 0)},
        {"type": "Images", "ext": ".jpg", "icon": "image", "count": ext_counter.get(".jpg", 0) + ext_counter.get(".png", 0)},
        {"type": "Excel Sheets", "ext": ".xlsx", "icon": "xlsx", "count": ext_counter.get(".xlsx", 0)},
        {"type": "PowerPoint", "ext": ".pptx", "icon": "ppt", "count": ext_counter.get(".pptx", 0) + ext_counter.get(".ppt", 0)},
        {"type": "CSV Files", "ext": ".csv", "icon": "csv", "count": ext_counter.get(".csv", 0)},
        {"type": "Text Files", "ext": ".txt", "icon": "text", "count": ext_counter.get(".txt", 0)},
        {"type": "XML Files", "ext": ".xml", "icon": "xml", "count": ext_counter.get(".xml", 0)},
        {"type": "Others", "ext": "other", "icon": "file", "count": sum(ext_counter.values()) - (
            ext_counter.get(".pdf", 0) +
            ext_counter.get(".docx", 0) +
            ext_counter.get(".jpg", 0) +
            ext_counter.get(".png", 0) +
            ext_counter.get(".xlsx", 0) +
            ext_counter.get(".pptx", 0) +
            ext_counter.get(".ppt", 0) +
            ext_counter.get(".csv", 0) +
            ext_counter.get(".txt", 0) +
            ext_counter.get(".xml", 0)
        )},
    ]

    if user.is_superuser:
        categories = FileCategory.objects.annotate(
            file_count=Count('file', filter=Q(file__is_deleted=False))
        )
    else:
        categories = FileCategory.objects.annotate(
            file_count=Count(
                'file',
                filter=(
                    Q(file__is_deleted=False) &
                    (
                        Q(file__access_level='public') |
                        Q(file__access_level='restricted', file__authorized_users=user) |
                        Q(file__access_level='confidential', file__uploaded_by=user)
                    )
                )
            )
        )

    recent_files_qs = files.order_by('-upload_date')[:10]  
    recent_files = []
    
    for file in recent_files_qs:
        if file.file_exists():
            file.extension = file.get_file_extension()
            recent_files.append(file)
            if len(recent_files) >= 5:  
                break

    visible_files = []
    for file in recent_files:
        if file.access_level == 'public' or user.is_superuser:
            file.extension = os.path.splitext(file.file.name)[1] 
            visible_files.append(file)
        elif file.access_level == 'restricted' and file.authorized_users.filter(id=user.id).exists() or user.is_superuser:
            file.extension = os.path.splitext(file.file.name)[1]
            visible_files.append(file)
        elif file.access_level == 'confidential' and (file.uploaded_by == user or user.is_superuser):
            file.extension = os.path.splitext(file.file.name)[1]
            visible_files.append(file)

    can_view_logs = request.user.has_perm('core.view_fileaccesslog')
    
    return render(request, 'core/file_management/dashboard.html', {
        'categories': categories,
        'recent_files': recent_files,  
        'file_types': file_types,
        'user_name': request.user.username,
        'can_view_logs': can_view_logs, 
    })

"""@login_required
def file_list_by_type_view(request, ext):
    user = request.user

    if user.is_superuser:
        files = File.objects.filter(is_deleted=False)
    else:
        files = File.objects.filter(
            is_deleted=False
        ).filter(
            Q(access_level__in=['public', 'restricted']) |
            Q(access_level='confidential', uploaded_by=user)
        )

    if ext != 'other':
        files = files.filter(file__iendswith=ext)
    else:
        known_exts = [
            '.pdf', '.docx', '.jpg', '.jpeg', '.png',
            '.xlsx', '.ppt', '.pptx', '.csv', '.txt', '.xml'
        ]

        exclude_q = Q()
        for e in known_exts:
            exclude_q |= Q(file__iendswith=e)

        files = files.exclude(exclude_q)

    can_view_logs = request.user.has_perm('core.view_fileaccesslog')

    return render(request, 'core/file_management/file_list.html', {
        'files': files,
        'file_type': ext,
        'can_view_logs': can_view_logs,
    })

@login_required
def file_list_view(request, category_name=None):
    user = request.user
    validated_files = request.session.get("validated_files", [])

    if user.is_superuser:
        files = File.objects.filter(is_deleted=False)
    else:
        files = File.objects.filter(
            is_deleted=False
        ).filter(
            Q(access_level__in=['public', 'restricted']) |
            Q(access_level='confidential', uploaded_by=user)
        )

    if category_name:
        files = files.filter(category__name__iexact=category_name)

    sort_option = request.GET.get('sort')
    if sort_option == 'recent':
        files = files.order_by('-upload_date')
    else:
        files = files.order_by('title')

    paginator = Paginator(files, 10)
    page = request.GET.get('page')

    try:
        paginated_files = paginator.page(page)
    except PageNotAnInteger:
        paginated_files = paginator.page(1)
    except EmptyPage:
        paginated_files = paginator.page(paginator.num_pages)

    categories = FileCategory.objects.all()
    highlight_file_id = request.GET.get("file_id")
    can_view_logs = request.user.has_perm('core.view_fileaccesslog')

    return render(request, 'core/file_management/file_list.html', {
        'files': paginated_files,
        'categories': categories,
        'active_category': category_name,
        'validated_files': validated_files,
        'can_view_logs': can_view_logs,
        'highlight_file_id': highlight_file_id,
        'recent': sort_option == 'recent',
    })"""

@login_required
def file_list_by_type_view(request, ext):
    user = request.user

    if user.is_superuser:
        files = File.objects.filter(is_deleted=False)
    else:
        files = File.objects.filter(
            is_deleted=False
        ).filter(
            Q(access_level__in=['public', 'restricted']) |
            Q(access_level='confidential', uploaded_by=user)
        )

    if ext != 'other':
        files = files.filter(file__iendswith=ext)
    else:
        known_exts = [
            '.pdf', '.docx', '.jpg', '.jpeg', '.png',
            '.xlsx', '.ppt', '.pptx', '.csv', '.txt', '.xml'
        ]

        exclude_q = Q()
        for e in known_exts:
            exclude_q |= Q(file__iendswith=e)

        files = files.exclude(exclude_q)

    # Filter out files that don't exist on filesystem
    existing_files = [f for f in files if f.file_exists()]

    can_view_logs = request.user.has_perm('core.view_fileaccesslog')

    return render(request, 'core/file_management/file_list.html', {
        'files': existing_files,
        'file_type': ext,
        'can_view_logs': can_view_logs,
    })

@login_required
def file_list_view(request, category_name=None):
    user = request.user
    validated_files = request.session.get("validated_files", [])

    if user.is_superuser:
        files = File.objects.filter(is_deleted=False)
    else:
        files = File.objects.filter(
            is_deleted=False
        ).filter(
            Q(access_level__in=['public', 'restricted']) |
            Q(access_level='confidential', uploaded_by=user)
        )

    if category_name:
        files = files.filter(category__name__iexact=category_name)

    sort_option = request.GET.get('sort')
    if sort_option == 'recent':
        files = files.order_by('-upload_date')
    else:
        files = files.order_by('title')

    existing_files = [f for f in files if f.file_exists()]

    paginator = Paginator(existing_files, 10)
    page = request.GET.get('page')

    try:
        paginated_files = paginator.page(page)
    except PageNotAnInteger:
        paginated_files = paginator.page(1)
    except EmptyPage:
        paginated_files = paginator.page(paginator.num_pages)

    categories = FileCategory.objects.all()
    highlight_file_id = request.GET.get("file_id")
    can_view_logs = request.user.has_perm('core.view_fileaccesslog')

    return render(request, 'core/file_management/file_list.html', {
        'files': paginated_files,
        'categories': categories,
        'active_category': category_name,
        'validated_files': validated_files,
        'can_view_logs': can_view_logs,
        'highlight_file_id': highlight_file_id,
        'recent': sort_option == 'recent',
    })
    

@login_required
def file_list_view(request, category_name=None):
    user = request.user
    validated_files = request.session.get("validated_files", [])

    if user.is_superuser:
        files = File.objects.filter(is_deleted=False)
    else:
        files = File.objects.filter(
            is_deleted=False
        ).filter(
            Q(access_level__in=['public', 'restricted']) |
            Q(access_level='confidential', uploaded_by=user)
        )

    if category_name:
        files = files.filter(category__name__iexact=category_name)

    sort_option = request.GET.get('sort')
    if sort_option == 'recent':
        files = files.order_by('-upload_date')
    else:
        files = files.order_by('title')

    existing_files = [f for f in files if f.file_exists()]

    paginator = Paginator(existing_files, 10)
    page = request.GET.get('page')

    try:
        paginated_files = paginator.page(page)
    except PageNotAnInteger:
        paginated_files = paginator.page(1)
    except EmptyPage:
        paginated_files = paginator.page(paginator.num_pages)

    categories = FileCategory.objects.all()
    highlight_file_id = request.GET.get("file_id")
    can_view_logs = request.user.has_perm('core.view_fileaccesslog')

    return render(request, 'core/file_management/file_list.html', {
        'files': paginated_files,
        'categories': categories,
        'active_category': category_name,
        'validated_files': validated_files,
        'can_view_logs': can_view_logs,
        'highlight_file_id': highlight_file_id,
        'recent': sort_option == 'recent',
    })

@login_required
def search(request):
    query = request.GET.get('q', '')

    files = File.objects.filter(title__icontains=query, is_deleted=False)
    categories = FileCategory.objects.filter(name__icontains=query)

    allowed_groups = ['Director', 'Staff', 'Manager']
    users = User.objects.filter(
        username__icontains=query,
        groups__name__in=allowed_groups
    ).distinct()  

    can_view_logs = (
        request.user.is_superuser or
        request.user.groups.filter(name='Director').exists() or
        request.user.groups.filter(name='Manager').exists()
    )

    context = {
        'query': query,
        'files': files,
        'categories': categories,
        'users': users,
        'can_view_logs': can_view_logs,
    }

    return render(request, 'core/file_management/search_result.html', context)

@login_required
def preview_file(request, file_id):
    file = get_object_or_404(File, id=file_id, is_deleted=False)

    # Check if file access has been validated
    validated_files = request.session.get("validated_files", [])
    if file.access_level == 'restricted' and file.id not in validated_files:
        raise PermissionDenied("Passcode required for restricted file.")

    # Ensure the uploader has allowed preview
    if file.access_level == 'restricted' and not file.allow_preview:
        raise PermissionDenied("Preview not allowed for this file.")

    # Access control based on access level
    if file.access_level == 'public':
        pass  # Public files can be freely previewed
    elif file.access_level == 'restricted':
        if not file.can_user_access(request.user):
            raise PermissionDenied("Access denied.")
    elif file.access_level == 'confidential':
        if request.user != file.uploaded_by and not request.user.is_superuser:
            raise PermissionDenied("Access denied for confidential file.")
    else:
        raise PermissionDenied("Unknown access level.")

    # Log access (preview)
    FileAccessLog.objects.create(file=file, accessed_by=request.user, action='preview')

    # Serve the file if it's previewable
    mime_type, _ = guess_type(file.file.name)
    if mime_type in ['application/pdf', 'image/jpeg', 'image/png', 'image/gif']:
        return FileResponse(file.file.open('rb'), content_type=mime_type)

    can_view_logs = (
        request.user.is_superuser or
        request.user.groups.filter(name='Director').exists() or
        request.user.groups.filter(name='Manager').exists()
    )

    # Unsupported type
    return render(request, 'core/file_management/unsupported_preview.html', {'file': file, 'can_view_logs': can_view_logs})



@login_required
def download_file(request, file_id):
    file = get_object_or_404(File, id=file_id, is_deleted=False)

    # Check if file access has been validated
    validated_files = request.session.get("validated_files", [])
    if file.access_level == 'restricted' and file.id not in validated_files:
        raise PermissionDenied("Passcode required for restricted file.")

    # Ensure the uploader has allowed download
    if file.access_level == 'restricted' and not file.allow_download:
        raise PermissionDenied("Download not allowed for this file.")

    # Access control based on access level
    if file.access_level == 'public':
        pass  # Public files can be freely downloaded
    elif file.access_level == 'restricted':
        if not file.can_user_access(request.user):
            raise PermissionDenied("Access denied.")
    elif file.access_level == 'confidential':
        if request.user != file.uploaded_by and not request.user.is_superuser:
            raise PermissionDenied("Access denied for confidential file.")
    else:
        raise PermissionDenied("Unknown access level.")

    # Log download
    FileAccessLog.objects.create(file=file, accessed_by=request.user, action='download')

    # Serve file for download
    response = FileResponse(file.file.open('rb'))
    response['Content-Disposition'] = f'attachment; filename="{file.file.name.split("/")[-1]}"'
    return response


@login_required
def file_access_logs(request):
    search_query = request.GET.get('search', '')
    logs = FileAccessLog.objects.all().order_by('-access_time')

    if search_query:
        logs = logs.filter(
            Q(file__title__icontains=search_query) | 
            Q(accessed_by__username__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(logs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Check if user has the required permissions
    can_view_logs = (
        request.user.is_superuser or
        request.user.groups.filter(name='Director').exists() or
        request.user.groups.filter(name='Manager').exists()
    )

    return render(request, 'core/file_management/file_access_logs.html', {
        'page_obj': page_obj,
        'can_view_logs': can_view_logs
    })

def user_can_manage_logs(user):
    return (
        user.is_superuser or
        user.groups.filter(name='Director').exists() or
        user.groups.filter(name='Manager').exists()
    )

@login_required
def delete_log(request, log_id):
    if not user_can_manage_logs(request.user):
        return redirect('file_access_logs')

    log = get_object_or_404(FileAccessLog, id=log_id)
    log.delete()
    return redirect('file_access_logs')


@login_required
def clear_all_logs(request):
    if not user_can_manage_logs(request.user):
        return redirect('file_access_logs')

    FileAccessLog.objects.all().delete()
    return redirect('file_access_logs')

    
@login_required
def delete_file(request, file_id):
    file = get_object_or_404(File, id=file_id, is_deleted=False)

    if not (
        request.user == file.uploaded_by
        or request.user.is_superuser
        or request.user.has_perm("core.delete_file")
    ):
        raise PermissionDenied("You do not have permission to delete this file")

    if request.method == "POST":
        file.is_deleted = True  # soft delete
        file.save()
        messages.success(request, "File deleted successfully.")
        return redirect("file_list")

    return redirect("file_list")
    
@login_required
@permission_required('core.add_file', raise_exception=True)
def upload_file_view(request):
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file_instance = form.save(commit=False)
            file_instance.uploaded_by = request.user
            file_instance.save()

            # Return file ID to frontend for AJAX passcode update
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"file_id": file_instance.id, "success": True})

            messages.success(request, 'File uploaded successfully!')
            return redirect('file_list')
    else:
        form = FileUploadForm()

    return render(request, 'core/file_management/upload_file.html', {'form': form})


@login_required
def update_passcode_view(request, file_id):
    file = get_object_or_404(File, id=file_id)

    if request.method == 'POST':
        # Ensure the user is the owner or superuser
        if file.uploaded_by != request.user and not request.user.is_superuser:
            return JsonResponse({"success": False, "error": "You do not have permission to update the passcode."}, status=403)

        passcode = request.POST.get('passcode')
        if passcode:
            file.passcode = passcode
            # Additional logic for controlling file actions (Preview/Download)
            file.allow_preview = request.POST.get('allow_preview', False) == 'true'
            file.allow_download = request.POST.get('allow_download', False) == 'true'
            file.save()
            return JsonResponse({"success": True})

        return JsonResponse({"success": False, "error": "No passcode provided"}, status=400)

    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)



@login_required
def validate_passcode(request, file_id):
    file = get_object_or_404(File, id=file_id)
    passcode = request.POST.get('passcode')

    print(f"Passcode from frontend: {passcode}, Stored passcode: {file.passcode}")

    if file.passcode == passcode:
        validated_files = request.session.get("validated_files", [])
        if file.id not in validated_files:
            validated_files.append(file.id)
            request.session["validated_files"] = validated_files
            request.session.modified = True  
            request.session.save() 

        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False}, status=400)



@login_required
def edit_file(request, file_id):
    #if not request.user.has_perm('core.change_file'):
        #raise PermissionDenied("You do not have permission to edit this file")
    if file.access_level == 'confidential' and file.uploaded_by != request.user and not request.user.is_superuser:
        raise PermissionDenied("This confidential file can only be edited by its uploader.")
    file = get_object_or_404(File, pk=file_id)

    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES, instance=file)
        if form.is_valid():
            form.save()
            return redirect('view_files')
    else:
        form = FileUploadForm(instance=file)

    return render(request, 'edit_file.html', {'form': form, 'file': file})


def custom_permission_denied(request, exception=None):
    can_view_logs = (
        request.user.is_superuser or
        request.user.groups.filter(name='Director').exists() or
        request.user.groups.filter(name='Manager').exists()
    )
    context = {
        "exception": str(exception),
        "can_view_logs": can_view_logs
    }
    return render(request, "core/file_management/403.html", context, status=403)


def user_can_manage_logs(user):
    return (
        user.is_superuser or
        user.groups.filter(name='Director').exists() or
        user.groups.filter(name='Manager').exists()
    )
