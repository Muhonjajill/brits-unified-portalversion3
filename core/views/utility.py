from .imports import *

@login_required
def profile_view(request):
    context = {
        'user': request.user,
        'user_form': UserUpdateForm(instance=request.user),
        'profile_form': ProfileUpdateForm(instance=request.user.profile),
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'accounts/profile_content.html', context)

    return render(request, 'accounts/profile.html', context)


class SettingsView(View):
    def get(self, request):
        user_form = UserUpdateForm(instance=request.user)
        profile, created = Profile.objects.get_or_create(user=request.user)
        profile_form = ProfileUpdateForm(instance=profile)

        return render(request, 'accounts/settings.html', {
            'user_form': user_form,
            'profile_form': profile_form
        })

    def post(self, request):
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile, created = Profile.objects.get_or_create(user=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your settings have been updated.")
            return redirect('settings') 

        print("FILES:", request.FILES)

        return render(request, 'accounts/settings.html', {
            'user_form': user_form,
            'profile_form': profile_form
        })

"""def export_tickets_to_excel(tickets):
    wb = Workbook()
    ws = wb.active
    ws.title = "Tickets"

    ws.append([
        "ID", "Terminal", "Issue", "Status",
        "Assigned To", "Created At"
    ])

    for ticket in tickets:
        ws.append([
            ticket.id,
            ticket.terminal.branch_name if ticket.terminal else "",
            ticket.title,
            ticket.get_status_display(),
            ticket.assigned_to.username if ticket.assigned_to else "",
            ticket.created_at.strftime("%Y-%m-%d %H:%M"),
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=tickets.xlsx"
    wb.save(response)

    return response"""

def export_tickets_to_excel(tickets, customer_name=None, terminal_name=None, start_date=None, end_date=None):
    wb = Workbook()
    ws = wb.active
    ws.title = "Tickets"

    ws.append([
        "ID", "Terminal", "Issue", "Status",
        "Assigned To", "Created At"
    ])

    for ticket in tickets:
        ws.append([
            ticket.id,
            ticket.terminal.branch_name if ticket.terminal else "",
            ticket.title,
            ticket.get_status_display(),
            ticket.assigned_to.username if ticket.assigned_to else "",
            ticket.created_at.strftime("%Y-%m-%d %H:%M"),
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=tickets.xlsx"
    wb.save(response)
    return response