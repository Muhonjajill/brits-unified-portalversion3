import io
import logging
from datetime import date, datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.text import get_valid_filename

from .forms import LeaveApplicationForm, LeaveDecisionForm
from .models import LeaveApplication, NOTICE_DAYS, NOTICE_EXEMPT_TYPES

User = get_user_model()
log = logging.getLogger(__name__)


# ─── Role helpers (same rules as claims) ──────────────────────────────────────

def _is_elevated(user):
    """Superusers, Managers and Directors see every submitted application."""
    if user.is_superuser:
        return True
    role = getattr(user, 'role', '') or ''
    if role.lower() in ('manager', 'director'):
        return True
    return user.groups.filter(name__in=['Manager', 'Director', 'Superadmin']).exists()


def _can_view(user, leave, elevated=None):
    if leave.status == LeaveApplication.STATUS_DRAFT:
        return user == leave.employee
    if elevated is None:
        elevated = _is_elevated(user)
    return elevated or user in (leave.employee, leave.manager)


def _can_delete(user, leave):
    """Elevated users can delete any application; employees only their own drafts."""
    if _is_elevated(user):
        return True
    return leave.employee == user and leave.status == LeaveApplication.STATUS_DRAFT


def _base_context(request):
    return {'can_view_logs': request.user.has_perm('core.view_fileaccesslog')}


# ─── Email (reports failures instead of hiding them) ──────────────────────────

def _leave_url(request, leave):
    try:
        return request.build_absolute_uri(reverse('leave_detail', kwargs={'pk': leave.pk}))
    except Exception:
        return ''


def _send_leave_email(subject, template, context, to_email, text_body):
    """Returns (sent, problem). HTML + plain-text; falls back to text if the template is missing."""
    to_email = (to_email or '').strip()
    if not to_email:
        return False, "the recipient has no email address on their account"
    try:
        html_body = render_to_string(template, context)
    except TemplateDoesNotExist:
        log.warning("%s not found; sending plain-text leave email", template)
        html_body = None
    try:
        msg = EmailMultiAlternatives(subject=subject, body=text_body,
                                     from_email=settings.DEFAULT_FROM_EMAIL, to=[to_email])
        if html_body:
            msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=False)
        return True, ''
    except Exception as exc:
        log.exception("Leave email to %s failed", to_email)
        return False, f"the mail server returned an error ({exc.__class__.__name__}: {exc})"


def _person(user):
    return (user.get_full_name() or user.username) if user else ''


def _period(leave):
    return f"{leave.start_date:%d %b %Y} – {leave.end_date:%d %b %Y}"


def _notify_manager(leave, request, event='submitted'):
    """Tell the approving manager a leave was submitted (or withdrawn)."""
    if not leave.manager:
        return False, "no approving manager is set"
    verb = 'submitted for your approval' if event == 'submitted' else 'withdrawn'
    subject = (f"[BRITS] Leave {'request' if event == 'submitted' else 'withdrawn'} — "
               f"{_person(leave.employee)} ({leave.get_leave_type_display()}, {_period(leave)})")
    url = _leave_url(request, leave)
    text = (
        f"Hi {_person(leave.manager)},\n\n"
        f"{_person(leave.employee)} has {verb} a {leave.type_label.lower()} leave application.\n\n"
        f"Dates: {_period(leave)} ({leave.working_days} working day{'s' if leave.working_days != 1 else ''})\n"
        f"Reason: {leave.reason}\n"
        + (f"\nWithdrawal reason: {leave.withdraw_reason}\n" if event == 'withdrawn' else '')
        + (f"\nReview it here: {url}\n" if url else '')
    )
    return _send_leave_email(subject, 'email/leave_submitted_email.html', {
        'leave': leave, 'event': event, 'recipient_name': _person(leave.manager),
        'employee_name': _person(leave.employee), 'leave_url': url,
    }, leave.manager.email, text)


def _notify_employee(leave, request):
    """Tell the employee their leave was approved or rejected."""
    outcome = 'approved' if leave.status == LeaveApplication.STATUS_APPROVED else 'rejected'
    subject = f"[BRITS] Your leave has been {outcome} — {leave.get_leave_type_display()}, {_period(leave)}"
    url = _leave_url(request, leave)
    text = (
        f"Hi {_person(leave.employee)},\n\n"
        f"{_person(leave.manager)} has {outcome} your {leave.type_label.lower()} leave "
        f"for {_period(leave)}.\n"
        + (f"\nComments: {leave.manager_comment}\n" if leave.manager_comment else '')
        + (f"\nView it here: {url}\n" if url else '')
    )
    return _send_leave_email(subject, 'email/leave_outcome_email.html', {
        'leave': leave, 'outcome': outcome, 'recipient_name': _person(leave.employee),
        'manager_name': _person(leave.manager), 'leave_url': url,
    }, leave.employee.email, text)


def _hr_emails():
    """
    HR address(es) that get a copy of every approved leave, from settings.py:
        LEAVE_HR_EMAIL = 'hr@example.com'          # or a list of addresses
    Returns [] when it isn't set, in which case no HR email is sent.
    """
    value = getattr(settings, 'LEAVE_HR_EMAIL', None)
    if not value:
        return []
    if isinstance(value, str):
        value = [value]
    return [v.strip() for v in value if v and v.strip()]


def _notify_hr(leave, request, event='approved'):
    """Record-keeping copy to HR: when leave is approved, or an approved leave is withdrawn."""
    recipients = _hr_emails()
    if not recipients:
        log.info("LEAVE_HR_EMAIL not set; skipping HR copy for leave %s", leave.pk)
        return True, ''
    url = _leave_url(request, leave)
    if event == 'approved':
        subject = (f"[BRITS] Leave approved (for HR records) — {_person(leave.employee)}, "
                   f"{leave.get_leave_type_display()}, {_period(leave)}")
        head = f"{_person(leave.manager)} has approved the following leave."
    else:
        subject = (f"[BRITS] Approved leave withdrawn (for HR records) — {_person(leave.employee)}, "
                   f"{leave.get_leave_type_display()}, {_period(leave)}")
        head = f"{_person(leave.employee)} has withdrawn the following previously approved leave."
    text = (
        f"{head}\n\n"
        f"Employee: {_person(leave.employee)} ({leave.employee_number or 'no employee number'})\n"
        f"Type: {leave.type_label}\n"
        f"Dates: {_period(leave)} ({leave.working_days} working day{'s' if leave.working_days != 1 else ''})\n"
        f"Reason: {leave.reason}\n"
        f"Approved by: {_person(leave.manager)}"
        + (f" on {timezone.localtime(leave.manager_actioned_at):%d %b %Y %H:%M}" if leave.manager_actioned_at else '') + "\n"
        + (f"Manager's comment: {leave.manager_comment}\n" if leave.manager_comment else '')
        + (f"\nWithdrawal reason: {leave.withdraw_reason}\n" if event == 'withdrawn' else '')
        + (f"\nView it here: {url}\n" if url else '')
    )
    sent_all, problems = True, []
    for addr in recipients:
        sent, problem = _send_leave_email(subject, 'email/leave_hr_record_email.html', {
            'leave': leave, 'event': event, 'employee_name': _person(leave.employee),
            'manager_name': _person(leave.manager), 'leave_url': url,
        }, addr, text)
        if not sent:
            sent_all = False
            problems.append(f"{addr}: {problem}")
    return sent_all, '; '.join(problems)


def _report_email(request, sent_problem, who):
    sent, problem = sent_problem
    if not sent:
        messages.warning(request, f"Note: the email to {who} could NOT be sent — {problem}.")


# ─── List ─────────────────────────────────────────────────────────────────────

def _parse_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


def _filtered_leaves(request, params):
    """Visibility rules + filters, shared by the list page and the Excel register."""
    user = request.user
    elevated = _is_elevated(user)
    qs = LeaveApplication.objects.select_related('employee', 'manager')
    if elevated:
        qs = qs.filter(~Q(status=LeaveApplication.STATUS_DRAFT) | Q(employee=user))
    else:
        qs = qs.filter(employee=user)

    f = {
        'search': params.get('q', '').strip(),
        'status_filter': params.get('status', '').strip(),
        'type_filter': params.get('type', '').strip(),
        'employee_filter': params.get('emp', '').strip(),
        'date_from': params.get('date_from', '').strip(),
        'date_to': params.get('date_to', '').strip(),
    }
    if f['search']:
        qs = qs.filter(
            Q(employee__first_name__icontains=f['search']) |
            Q(employee__last_name__icontains=f['search']) |
            Q(employee__username__icontains=f['search']) |
            Q(employee_number__icontains=f['search']) |
            Q(reason__icontains=f['search'])
        )
    if f['status_filter']:
        qs = qs.filter(status=f['status_filter'])
    if f['type_filter']:
        qs = qs.filter(leave_type=f['type_filter'])
    if f['employee_filter'] and elevated:
        qs = qs.filter(employee__id=f['employee_filter'])
    # Date range: any leave that overlaps the chosen period
    d_from, d_to = _parse_date(f['date_from']), _parse_date(f['date_to'])
    if d_from:
        qs = qs.filter(end_date__gte=d_from)
    if d_to:
        qs = qs.filter(start_date__lte=d_to)
    return qs, f


@login_required
def leave_list(request):
    user = request.user
    elevated = _is_elevated(user)
    qs, f = _filtered_leaves(request, request.GET)

    pending_approvals = LeaveApplication.objects.filter(
        manager=user, status=LeaveApplication.STATUS_SUBMITTED
    ).select_related('employee').order_by('start_date')

    page_obj = Paginator(qs, 10).get_page(request.GET.get('page'))

    summary = None
    if elevated:
        year_start = date(date.today().year, 1, 1)
        approved_this_year = qs.filter(status=LeaveApplication.STATUS_APPROVED, start_date__gte=year_start)
        summary = {
            'total': qs.count(),
            'pending': qs.filter(status=LeaveApplication.STATUS_SUBMITTED).count(),
            'approved': qs.filter(status=LeaveApplication.STATUS_APPROVED).count(),
            'rejected': qs.filter(status=LeaveApplication.STATUS_REJECTED).count(),
            'days_this_year': sum(l.working_days for l in approved_this_year),
        }

    employees_for_filter = []
    if elevated:
        employees_for_filter = User.objects.filter(
            leave_applications__isnull=False
        ).distinct().order_by('first_name', 'last_name')

    qd = request.GET.copy()
    qd.pop('page', None)

    return render(request, 'core/leaves/leave_list.html', {
        **_base_context(request),
        'page_obj': page_obj,
        'pending_approvals': pending_approvals,
        'page_title': 'All Leave Applications' if elevated else 'My Leave',
        'elevated': elevated,
        'summary': summary,
        'status_choices': LeaveApplication.STATUS_CHOICES,
        'type_choices': LeaveApplication.TYPE_CHOICES,
        'employees_for_filter': employees_for_filter,
        'filter_querystring': qd.urlencode(),
        'today': date.today(),
        **f,
    })


# ─── Create / Edit ────────────────────────────────────────────────────────────

def _form_context(request, form, is_new, leave=None):
    return {
        **_base_context(request),
        'form': form,
        'is_new': is_new,
        'leave': leave,
        'notice_days': NOTICE_DAYS,
        'notice_exempt_types': list(NOTICE_EXEMPT_TYPES),
        'today': date.today(),
        'page_title': 'New Leave Application' if is_new else 'Edit Leave Application',
    }


def _save_and_maybe_submit(request, form, leave_is_new):
    leave = form.save(commit=False)
    if leave_is_new:
        leave.employee = request.user
    action = request.POST.get('action', 'save')
    if action == 'submit':
        leave.save()
        leave.submit()
        sent = _notify_manager(leave, request, 'submitted')
        messages.success(request, f"Leave application submitted to {_person(leave.manager)} for approval.")
        _report_email(request, sent, _person(leave.manager))
    else:
        leave.save()
        messages.success(request, "Leave application saved as draft.")
    return leave


@login_required
def leave_create(request):
    user = request.user
    if request.method == 'POST':
        form = LeaveApplicationForm(request.POST, employee=user,
                                    submitting=request.POST.get('action') == 'submit')
        if form.is_valid():
            leave = _save_and_maybe_submit(request, form, leave_is_new=True)
            return redirect('leave_detail', pk=leave.pk)
    else:
        # Prefill employee number and manager from the user's last application
        last = LeaveApplication.objects.filter(employee=user).order_by('-created_at').first()
        initial = {}
        if last:
            initial = {'employee_number': last.employee_number, 'manager': last.manager_id}
        form = LeaveApplicationForm(initial=initial, employee=user)
    return render(request, 'core/leaves/leave_form.html', _form_context(request, form, True))


@login_required
def leave_edit(request, pk):
    leave = get_object_or_404(LeaveApplication, pk=pk)
    if leave.employee != request.user or not leave.is_editable:
        messages.error(request, "This leave application can no longer be edited.")
        return redirect('leave_detail', pk=pk)
    if request.method == 'POST':
        form = LeaveApplicationForm(request.POST, instance=leave, employee=request.user,
                                    submitting=request.POST.get('action') == 'submit')
        if form.is_valid():
            _save_and_maybe_submit(request, form, leave_is_new=False)
            return redirect('leave_detail', pk=pk)
    else:
        form = LeaveApplicationForm(instance=leave, employee=request.user)
    return render(request, 'core/leaves/leave_form.html', _form_context(request, form, False, leave))


# ─── Detail ───────────────────────────────────────────────────────────────────

@login_required
def leave_detail(request, pk):
    leave = get_object_or_404(LeaveApplication.objects.select_related('employee', 'manager'), pk=pk)
    user = request.user
    elevated = _is_elevated(user)
    if not _can_view(user, leave, elevated):
        messages.error(request, "You do not have access to this leave application.")
        return redirect('leave_list')

    history = (LeaveApplication.objects.filter(employee=leave.employee)
               .exclude(pk=leave.pk).exclude(status=LeaveApplication.STATUS_DRAFT)
               .order_by('-start_date')[:5])

    can_withdraw = (
        user == leave.employee and (
            leave.status == LeaveApplication.STATUS_SUBMITTED or
            (leave.status == LeaveApplication.STATUS_APPROVED and leave.start_date > date.today())
        )
    )
    return render(request, 'core/leaves/leave_detail.html', {
        **_base_context(request),
        'leave': leave,
        'can_approve': leave.can_approve(user),
        'can_edit': user == leave.employee and leave.is_editable,
        'can_withdraw': can_withdraw,
        'can_delete': _can_delete(user, leave),
        'history': history,
        'elevated': elevated,
    })


# ─── Approve / reject / withdraw / delete ─────────────────────────────────────

@login_required
def leave_approve(request, pk):
    if request.method != 'POST':
        return redirect('leave_detail', pk=pk)
    leave = get_object_or_404(LeaveApplication, pk=pk)
    if not leave.can_approve(request.user):
        messages.error(request, "You are not authorised to approve this leave application.")
        return redirect('leave_detail', pk=pk)
    form = LeaveDecisionForm(request.POST)
    form.is_valid()
    leave.approve(request.user, comment=(form.cleaned_data.get('comment') or '').strip())
    sent = _notify_employee(leave, request)
    hr_sent = _notify_hr(leave, request, 'approved')
    messages.success(request, f"Leave approved. {_person(leave.employee)} has been notified"
                              f"{' and HR has a copy for their records' if _hr_emails() else ''}.")
    _report_email(request, sent, _person(leave.employee))
    _report_email(request, hr_sent, "HR")
    return redirect('leave_detail', pk=pk)


@login_required
def leave_reject(request, pk):
    if request.method != 'POST':
        return redirect('leave_detail', pk=pk)
    leave = get_object_or_404(LeaveApplication, pk=pk)
    if not leave.can_approve(request.user):
        messages.error(request, "You are not authorised to action this leave application.")
        return redirect('leave_detail', pk=pk)
    form = LeaveDecisionForm(request.POST)
    form.is_valid()
    comment = (form.cleaned_data.get('comment') or '').strip()
    if not comment:
        messages.error(request, "A comment is required when rejecting a leave application.")
        return redirect('leave_detail', pk=pk)
    leave.reject(request.user, comment=comment)
    sent = _notify_employee(leave, request)
    messages.warning(request, f"Leave rejected. {_person(leave.employee)} has been notified.")
    _report_email(request, sent, _person(leave.employee))
    return redirect('leave_detail', pk=pk)


@login_required
def leave_withdraw(request, pk):
    if request.method != 'POST':
        return redirect('leave_detail', pk=pk)
    leave = get_object_or_404(LeaveApplication, pk=pk)
    allowed = request.user == leave.employee and (
        leave.status == LeaveApplication.STATUS_SUBMITTED or
        (leave.status == LeaveApplication.STATUS_APPROVED and leave.start_date > date.today())
    )
    if not allowed:
        messages.error(request, "This leave application can no longer be withdrawn.")
        return redirect('leave_detail', pk=pk)
    reason = (request.POST.get('reason') or '').strip()
    if not reason:
        messages.error(request, "Please state why you are withdrawing this leave application.")
        return redirect('leave_detail', pk=pk)
    leave.withdraw(reason)
    sent = _notify_manager(leave, request, 'withdrawn')
    messages.success(request, "Leave application withdrawn. Your manager has been notified.")
    _report_email(request, sent, _person(leave.manager))
    if leave.was_approved_before_withdrawal:
        _report_email(request, _notify_hr(leave, request, 'withdrawn'), "HR")
    return redirect('leave_detail', pk=pk)


@login_required
def leave_delete(request, pk):
    leave = get_object_or_404(LeaveApplication, pk=pk)
    if not _can_delete(request.user, leave):
        messages.error(request, "You do not have permission to delete this leave application.")
        return redirect('leave_detail', pk=pk)
    if request.method == 'POST':
        label = f"{_person(leave.employee)} ({_period(leave)})"
        leave.delete()
        messages.success(request, f"Leave application for {label} has been deleted.")
        return redirect('leave_list')
    return redirect('leave_detail', pk=pk)


# ─── Exports ──────────────────────────────────────────────────────────────────

def _safe_name(value, fallback='leave'):
    try:
        return get_valid_filename(value) or fallback
    except Exception:
        return fallback


def _leave_filename(leave, ext):
    """e.g. leave_Jane_Wanjiru_vacation_2026-12-01_to_2026-12-05.pdf"""
    name = _safe_name(leave.employee.get_full_name() or leave.employee.username)
    return f"leave_{name}_{leave.leave_type}_{leave.start_date:%Y-%m-%d}_to_{leave.end_date:%Y-%m-%d}.{ext}"


@login_required
def leave_export_pdf(request, pk):
    leave = get_object_or_404(LeaveApplication.objects.select_related('employee', 'manager'), pk=pk)
    if not _can_view(request.user, leave):
        return HttpResponse("Forbidden", status=403)
    try:
        from weasyprint import HTML
    except ImportError:
        return HttpResponse("WeasyPrint is not installed. Run: pip install weasyprint", status=500)
    html_string = render_to_string('core/leaves/leave_pdf.html', {
        'leave': leave, 'type_choices': LeaveApplication.TYPE_CHOICES,
        'notice_days': NOTICE_DAYS,
    })
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{_leave_filename(leave, "pdf")}"'
    return response


@login_required
def leave_export_excel(request):
    """Register of every application matching the current list filters."""
    try:
        import openpyxl
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        return HttpResponse("openpyxl is not installed. Run: pip install openpyxl", status=500)

    qs, f = _filtered_leaves(request, request.GET)
    qs = qs.order_by('start_date')

    def naive(dt):
        if not dt:
            return None
        return (timezone.localtime(dt) if timezone.is_aware(dt) else dt).replace(tzinfo=None)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Leave Register"
    thin = Side(style='thin')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    headers = [
        ('ID', 7), ('Employee', 24), ('Employee No.', 14), ('Type', 22), ('From', 12), ('To', 12),
        ('Working Days', 12), ('Status', 12), ('Manager', 22), ('Submitted', 17),
        ('Decided', 17), ('Reason', 40), ('Manager Comment', 40), ('Withdrawal Reason', 40),
    ]
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
    ws['A1'] = f"Leave register — generated {date.today():%d %b %Y}"
    ws['A1'].font = Font(bold=True, size=13)
    for col, (label, width) in enumerate(headers, start=1):
        c = ws.cell(row=2, column=col, value=label)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F3864")
        c.border = border
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.freeze_panes = 'C3'

    row = 3
    total_days = 0
    for lv in qs:
        values = [
            lv.pk, _person(lv.employee), lv.employee_number, lv.type_label,
            lv.start_date, lv.end_date, lv.working_days, lv.get_status_display(),
            _person(lv.manager), naive(lv.submitted_at), naive(lv.manager_actioned_at),
            lv.reason, lv.manager_comment, lv.withdraw_reason,
        ]
        for col, val in enumerate(values, start=1):
            c = ws.cell(row=row, column=col, value=val)
            c.border = border
            c.alignment = Alignment(vertical='top', wrap_text=col in (12, 13, 14))
            if col in (5, 6) and val:
                c.number_format = 'DD/MM/YYYY'
            elif col in (10, 11) and val:
                c.number_format = 'DD/MM/YYYY HH:MM'
        if lv.status == LeaveApplication.STATUS_APPROVED:
            total_days += lv.working_days
        row += 1
    ws.cell(row=row, column=1, value="Approved working days").font = Font(bold=True)
    ws.cell(row=row, column=7, value=total_days).font = Font(bold=True)

    out = io.BytesIO()
    wb.save(out)
    response = HttpResponse(out.getvalue(),
                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="leave_register_{date.today():%Y-%m-%d}.xlsx"'
    return response
