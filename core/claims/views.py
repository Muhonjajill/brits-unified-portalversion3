from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

from .models import ClaimForm, ClaimEntry
from .forms import ClaimFormForm, ClaimEntryFormSet, ApprovalActionForm


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _send_claim_email(subject, template, context, recipient_email):
    """Send a claim notification email."""
    try:
        body = render_to_string(template, context)
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=True,
        )
    except Exception:
        pass  # Never let email failure crash the view


def _notify_next_approver(claim):
    """Email the next person in the approval chain."""
    if claim.status == ClaimForm.STATUS_SUBMITTED and claim.manager:
        _send_claim_email(
            subject=f"[BRITS] Claim awaiting your approval — {claim.employee.get_full_name()}",
            template='core/claims/email_approval_request.txt',
            context={'claim': claim, 'role': 'Manager'},
            recipient_email=claim.manager.email,
        )
    elif claim.status == ClaimForm.STATUS_MANAGER_APPROVED and claim.hr_reviewer:
        _send_claim_email(
            subject=f"[BRITS] Claim awaiting HR review — {claim.employee.get_full_name()}",
            template='core/claims/email_approval_request.txt',
            context={'claim': claim, 'role': 'HR'},
            recipient_email=claim.hr_reviewer.email,
        )
    elif claim.status == ClaimForm.STATUS_HR_APPROVED and claim.finance_reviewer:
        _send_claim_email(
            subject=f"[BRITS] Claim awaiting Finance approval — {claim.employee.get_full_name()}",
            template='core/claims/email_approval_request.txt',
            context={'claim': claim, 'role': 'Finance'},
            recipient_email=claim.finance_reviewer.email,
        )


def _notify_employee_outcome(claim):
    """Email the employee when their claim is fully approved or rejected."""
    if claim.status in (ClaimForm.STATUS_FINANCE_APPROVED, ClaimForm.STATUS_REJECTED):
        _send_claim_email(
            subject=f"[BRITS] Your claim has been {claim.get_status_display().lower()}",
            template='core/claims/email_outcome.txt',
            context={'claim': claim},
            recipient_email=claim.employee.email,
        )


# ─── Employee views ────────────────────────────────────────────────────────────

@login_required
def claim_list(request):
    """Employee's own claims + any pending approvals for this user."""
    my_claims = ClaimForm.objects.filter(employee=request.user).select_related('employee')

    pending_approvals = ClaimForm.objects.filter(
        Q(manager=request.user, status=ClaimForm.STATUS_SUBMITTED) |
        Q(hr_reviewer=request.user, status=ClaimForm.STATUS_MANAGER_APPROVED) |
        Q(finance_reviewer=request.user, status=ClaimForm.STATUS_HR_APPROVED)
    ).select_related('employee')


    can_view_logs = request.user.has_perm('core.view_fileaccesslog')

    context = {
        'my_claims': my_claims,
        'pending_approvals': pending_approvals,
        'page_title': 'My Claims',
        'can_view_logs': can_view_logs,
    }
    return render(request, 'core/claims/claim_list.html', context)


@login_required
def claim_create(request):
    """Create a new claim form with inline entries."""
    if request.method == 'POST':
        form = ClaimFormForm(request.POST)
        formset = ClaimEntryFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            claim = form.save(commit=False)
            claim.employee = request.user
            claim.save()
            formset.instance = claim
            formset.save()
            action = request.POST.get('action', 'save')
            if action == 'submit':
                claim.status = ClaimForm.STATUS_SUBMITTED
                claim.submitted_at = timezone.now()
                claim.save()
                _notify_next_approver(claim)
                messages.success(request, "Claim submitted for manager approval.")
            else:
                messages.success(request, "Claim saved as draft.")
            return redirect('claim_detail', pk=claim.pk)
    else:
        form = ClaimFormForm()
        formset = ClaimEntryFormSet()

    can_view_logs = request.user.has_perm('core.view_fileaccesslog')

    return render(request, 'core/claims/claim_form.html', {
        'form': form,
        'formset': formset,
        'page_title': 'New Claim',
        'is_new': True,
        'can_view_logs': can_view_logs,
    })


@login_required
def claim_edit(request, pk):
    """Edit a draft or rejected claim."""
    claim = get_object_or_404(ClaimForm, pk=pk, employee=request.user)
    if claim.status not in (ClaimForm.STATUS_DRAFT, ClaimForm.STATUS_REJECTED):
        messages.error(request, "Only draft or rejected claims can be edited.")
        return redirect('claim_detail', pk=pk)

    if request.method == 'POST':
        form = ClaimFormForm(request.POST, instance=claim)
        formset = ClaimEntryFormSet(request.POST, instance=claim)
        if form.is_valid() and formset.is_valid():
            claim = form.save()
            formset.save()
            action = request.POST.get('action', 'save')
            if action == 'submit':
                claim.status = ClaimForm.STATUS_SUBMITTED
                claim.submitted_at = timezone.now()
                claim.save()
                _notify_next_approver(claim)
                messages.success(request, "Claim re-submitted for approval.")
            else:
                messages.success(request, "Claim updated.")
            return redirect('claim_detail', pk=pk)
    else:
        form = ClaimFormForm(instance=claim)
        formset = ClaimEntryFormSet(instance=claim)

    can_view_logs = request.user.has_perm('core.view_fileaccesslog')

    return render(request, 'core/claims/claim_form.html', {
        'form': form,
        'formset': formset,
        'claim': claim,
        'page_title': 'Edit Claim',
        'is_new': False,
        'can_view_logs': can_view_logs,
    })


@login_required
def claim_detail(request, pk):
    """View a single claim — employee or any approver."""
    claim = get_object_or_404(
        ClaimForm.objects.select_related('employee', 'manager', 'hr_reviewer', 'finance_reviewer')
                         .prefetch_related('entries'),
        pk=pk
    )
    # Only allow: the employee, or assigned approvers
    allowed = [claim.employee, claim.manager, claim.hr_reviewer, claim.finance_reviewer]
    if request.user not in allowed and not request.user.is_staff:
        messages.error(request, "You do not have access to this claim.")
        return redirect('claim_list')

    approval_form = ApprovalActionForm()
    can_approve = claim.can_approve(request.user)

    can_view_logs = request.user.has_perm('core.view_fileaccesslog')

    return render(request, 'core/claims/claim_detail.html', {
        'claim': claim,
        'entries': claim.entries.all(),
        'approval_form': approval_form,
        'can_approve': can_approve,
        'page_title': f"Claim — {claim.employee.get_full_name()}",
        'can_view_logs': can_view_logs,
    })


# ─── Approval views ────────────────────────────────────────────────────────────

@login_required
def claim_approve(request, pk):
    if request.method != 'POST':
        return redirect('claim_detail', pk=pk)
    claim = get_object_or_404(ClaimForm, pk=pk)
    if not claim.can_approve(request.user):
        messages.error(request, "You are not authorised to approve this claim at this stage.")
        return redirect('claim_detail', pk=pk)
    form = ApprovalActionForm(request.POST)
    if form.is_valid():
        claim.approve(request.user, comment=form.cleaned_data.get('comment', ''))
        _notify_next_approver(claim)
        _notify_employee_outcome(claim)
        messages.success(request, f"Claim approved. Status: {claim.get_status_display()}")
    return redirect('claim_detail', pk=pk)


@login_required
def claim_reject(request, pk):
    if request.method != 'POST':
        return redirect('claim_detail', pk=pk)
    claim = get_object_or_404(ClaimForm, pk=pk)
    if not claim.can_approve(request.user):
        messages.error(request, "You are not authorised to action this claim.")
        return redirect('claim_detail', pk=pk)
    form = ApprovalActionForm(request.POST)
    if form.is_valid():
        comment = form.cleaned_data.get('comment', '')
        if not comment:
            messages.error(request, "A comment is required when rejecting a claim.")
            return redirect('claim_detail', pk=pk)
        claim.reject(request.user, comment=comment)
        _notify_employee_outcome(claim)
        messages.warning(request, "Claim rejected. Employee has been notified.")
    return redirect('claim_detail', pk=pk)


# ─── Export views ──────────────────────────────────────────────────────────────

@login_required
def claim_export_pdf(request, pk):
    """Render the claim as a PDF using weasyprint."""
    claim = get_object_or_404(
        ClaimForm.objects.select_related('employee').prefetch_related('entries'),
        pk=pk
    )
    allowed = [claim.employee, claim.manager, claim.hr_reviewer, claim.finance_reviewer]
    if request.user not in allowed and not request.user.is_staff:
        return HttpResponse("Forbidden", status=403)

    try:
        from weasyprint import HTML
        html_string = render_to_string('core/claims/claim_pdf.html', {'claim': claim})
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        filename = f"claim_{claim.employee.get_full_name().replace(' ', '_')}_{claim.month.strftime('%Y_%m')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except ImportError:
        return HttpResponse(
            "WeasyPrint is not installed. Run: pip install weasyprint",
            status=500
        )


@login_required
def claim_export_excel(request, pk):
    """Export the claim to an .xlsx file matching the existing template layout."""
    claim = get_object_or_404(
        ClaimForm.objects.select_related('employee').prefetch_related('entries'),
        pk=pk
    )
    allowed = [claim.employee, claim.manager, claim.hr_reviewer, claim.finance_reviewer]
    if request.user not in allowed and not request.user.is_staff:
        return HttpResponse("Forbidden", status=403)

    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Claim Form"

        # ── Styles ──
        header_font = Font(bold=True, size=13)
        bold = Font(bold=True)
        center = Alignment(horizontal='center', vertical='center')
        right = Alignment(horizontal='right')
        thin = Side(style='thin')
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        navy_fill = PatternFill("solid", fgColor="1F3864")
        navy_font = Font(bold=True, color="FFFFFF")

        def style_cell(cell, font=None, align=None, fill=None, border_=None):
            if font: cell.font = font
            if align: cell.alignment = align
            if fill: cell.fill = fill
            if border_: cell.border = border_

        # ── Title ──
        ws.merge_cells('A1:K1')
        ws['A1'] = f"{claim.employee.get_full_name().upper()} CLAIM FORM"
        style_cell(ws['A1'], font=header_font, align=center)
        ws.row_dimensions[1].height = 28

        # ── Column header row ──
        headers = ['DATE', 'SITE', 'JOB CARD ID', 'TO', 'FROM',
                   'BREAKFAST', 'LUNCH', 'DINNER', 'BED', 'TOTAL', 'ADVANCE']
        col_widths = [14, 22, 16, 10, 10, 12, 10, 10, 10, 12, 12]
        for col_idx, (h, w) in enumerate(zip(headers, col_widths), start=1):
            cell = ws.cell(row=2, column=col_idx, value=h)
            style_cell(cell, font=navy_font, align=center, fill=navy_fill, border_=border)
            ws.column_dimensions[get_column_letter(col_idx)].width = w
        ws.row_dimensions[2].height = 20

        # ── Data rows ──
        for row_idx, entry in enumerate(claim.entries.all(), start=3):
            row_data = [
                entry.date,
                entry.site,
                entry.job_card_id,
                float(entry.transport_to),
                float(entry.transport_from),
                float(entry.breakfast),
                float(entry.lunch),
                float(entry.dinner),
                float(entry.bed),
                float(entry.total),
                '',
            ]
            for col_idx, val in enumerate(row_data, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.border = border
                if col_idx == 1:
                    cell.number_format = 'DD/MM/YYYY'
                    cell.alignment = center
                elif col_idx >= 4:
                    cell.number_format = '#,##0.00'
                    cell.alignment = right

        # ── Subtotal / totals ──
        last_data_row = 2 + claim.entries.count()
        subtotal_row = last_data_row + 2

        ws.merge_cells(f'A{subtotal_row}:I{subtotal_row}')
        ws.cell(subtotal_row, 1, 'Sub total').font = bold
        ws.cell(subtotal_row, 1).alignment = right
        ws.cell(subtotal_row, 10, float(claim.subtotal)).number_format = '#,##0.00'
        ws.cell(subtotal_row, 10).font = bold
        ws.cell(subtotal_row, 11, float(claim.advance)).number_format = '#,##0.00'
        ws.cell(subtotal_row, 11).font = bold

        tma_row = subtotal_row + 1
        ws.merge_cells(f'A{tma_row}:I{tma_row}')
        ws.cell(tma_row, 1, 'Total Minus Advance').font = bold
        ws.cell(tma_row, 1).alignment = right
        ws.cell(tma_row, 10, float(claim.total_minus_advance)).number_format = '#,##0.00'
        ws.cell(tma_row, 10).font = bold

        # ── Signature rows ──
        sig_row = tma_row + 3
        ws.cell(sig_row, 1, 'EMPLOYEE SIGN').font = bold
        ws.cell(sig_row, 5, 'DATE').font = bold
        ws.cell(sig_row + 1, 1, 'MANAGER SIGN').font = bold
        ws.cell(sig_row + 1, 5, 'DATE').font = bold
        ws.cell(sig_row + 2, 1, 'HR SIGN').font = bold
        ws.cell(sig_row + 2, 5, 'DATE').font = bold
        ws.cell(sig_row + 3, 1, 'FINANCE SIGN').font = bold
        ws.cell(sig_row + 3, 5, 'DATE').font = bold

        # ── Write response ──
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"claim_{claim.employee.get_full_name().replace(' ', '_')}_{claim.month.strftime('%Y_%m')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        return response

    except ImportError:
        return HttpResponse("openpyxl is not installed. Run: pip install openpyxl", status=500)
