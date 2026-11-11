from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse, QueryDict
from django.db.models import Q, Sum
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.utils.text import get_valid_filename
from django.urls import reverse
from decimal import Decimal
from datetime import date, datetime
import io
import zipfile

from .models import ClaimForm, ClaimEntry, PaymentRecord, ClaimPenalty
from .forms import ClaimFormForm, ClaimEntryFormSet, ApprovalActionForm, PaymentRecordForm, SuggestedAmountForm, PenaltyForm
from django.db import transaction

User = get_user_model()


# ─── Role helpers ──────────────────────────────────────────────────────────────

def _is_elevated(user):
    """True for superadmin, managers, and directors — can view/delete all claims."""
    if user.is_superuser:
        return True
    role = getattr(user, 'role', '').lower() if hasattr(user, 'role') else ''
    if role in ('manager', 'director'):
        return True
    return user.groups.filter(name__in=['Manager', 'Director', 'Superadmin']).exists()


def _is_finance(user):
    """True if the user is a Finance reviewer / elevated user who can record disbursements."""
    if user.is_superuser:
        return True
    role = getattr(user, 'role', '').lower() if hasattr(user, 'role') else ''
    if role in ('finance', 'director', 'manager'):
        return True
    return user.groups.filter(name__in=['Finance', 'Director', 'Superadmin']).exists()


def _can_delete(user):
    """Only superadmin, manager, and director may delete claims."""
    return _is_elevated(user)


# ─── One open claim at a time ─────────────────────────────────────────────────

# A claim is "open" from submission until Finance closes it. Drafts and
# rejected claims are not open, so they don't block anything.
OPEN_CLAIM_STATUSES = (
    ClaimForm.STATUS_SUBMITTED,
    ClaimForm.STATUS_MANAGER_APPROVED,
    ClaimForm.STATUS_PENDING_DISBURSEMENT,
)


def _open_claim_for(user, exclude_pk=None):
    """The user's own claim that is submitted but not yet closed, if any."""
    qs = ClaimForm.objects.filter(employee=user, status__in=OPEN_CLAIM_STATUSES)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.order_by('submitted_at').first()


def _open_claim_message(claim):
    return (
        f"You already have a claim in progress ({claim.month.strftime('%B %Y')}, "
        f"{claim.get_status_display()}). You can start or submit another claim "
        f"once it has been closed."
    )


# ─── Email helpers ─────────────────────────────────────────────────────────────

def _send_claim_email(subject, template, context, recipient_email):
    """Send an HTML claim notification email."""
    try:
        html_body = render_to_string(template, context)
        msg = EmailMessage(
            subject=subject,
            body=html_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        msg.content_subtype = 'html'
        msg.send(fail_silently=True)
    except Exception:
        pass


def _build_claim_url(request, claim):
    """Absolute URL to the claim detail page."""
    try:
        from django.urls import reverse
        return request.build_absolute_uri(reverse('claim_detail', kwargs={'pk': claim.pk}))
    except Exception:
        return ''


def _notify_submitted(claim, request=None):
    """
    Notify the assigned manager when an employee submits a claim.
    """
    if claim.manager and claim.manager.email:
        claim_url = _build_claim_url(request, claim) if request else ''
        _send_claim_email(
            subject=f"[BRITS] Claim submitted — {claim.employee.get_full_name()} ({claim.month.strftime('%B %Y')})",
            template='email/claim_submitted_email.html',
            context={
                'claim': claim,
                'approver_name': claim.manager.get_full_name() or claim.manager.username,
                'role': 'Manager',
                'claim_url': claim_url,
            },
            recipient_email=claim.manager.email,
        )


def _notify_manager_actioned(claim, request=None):
    """
    After manager approves → notify Finance reviewer.
    After manager rejects  → notify Employee.
    """
    claim_url = _build_claim_url(request, claim) if request else ''

    if claim.status == ClaimForm.STATUS_MANAGER_APPROVED and claim.finance_reviewer and claim.finance_reviewer.email:
        _send_claim_email(
            subject=f"[BRITS] Claim awaiting Finance approval — {claim.employee.get_full_name()} ({claim.month.strftime('%B %Y')})",
            template='email/claim_manager_actioned_email.html',
            context={
                'claim': claim,
                'recipient_name': claim.finance_reviewer.get_full_name() or claim.finance_reviewer.username,
                'claim_url': claim_url,
            },
            recipient_email=claim.finance_reviewer.email,
        )

    elif claim.status == ClaimForm.STATUS_REJECTED and claim.employee and claim.employee.email:
        _send_claim_email(
            subject=f"[BRITS] Your claim has been rejected — {claim.month.strftime('%B %Y')}",
            template='email/claim_manager_actioned_email.html',
            context={
                'claim': claim,
                'recipient_name': claim.employee.get_full_name() or claim.employee.username,
                'claim_url': claim_url,
            },
            recipient_email=claim.employee.email,
        )


def _notify_finance_outcome(claim, request=None):
    """
    After Finance approves or rejects → notify the Employee.
    """
    if claim.employee and claim.employee.email:
        claim_url = _build_claim_url(request, claim) if request else ''
        status_label = 'approved' if claim.status == ClaimForm.STATUS_FINANCE_APPROVED else 'rejected'
        _send_claim_email(
            subject=f"[BRITS] Your claim has been {status_label} — {claim.month.strftime('%B %Y')}",
            template='email/claim_finance_outcome_email.html',
            context={
                'claim': claim,
                'claim_url': claim_url,
            },
            recipient_email=claim.employee.email,
        )


# Built-in copy of email/claim_penalized_email.html, used if that template
# file can't be found, so the penalty email is never silently skipped.
_PENALTY_EMAIL_FALLBACK = """<!DOCTYPE html>
<html lang="en">
<body style="margin:0; padding:0; background:#f4f6fa; font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color:#343a40;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6fa; padding:24px 0;">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px; width:100%; background:#ffffff; border-radius:10px; overflow:hidden; border:1px solid #dee2e6;">
        <tr>
          <td style="background:#123692; color:#ffffff; padding:18px 24px; font-size:18px; font-weight:600;">
            Penalty on your claim
          </td>
        </tr>
        <tr>
          <td style="padding:24px; font-size:14px; line-height:1.6;">
            <p style="margin:0 0 12px;">Hi {{ recipient_name }},</p>
            <p style="margin:0 0 16px;">
              {{ penalized_by_name }} has placed a penalty on your
              <strong>{{ claim.month|date:"F Y" }}</strong> claim
              {% if claim.submitted_at %}(submitted {{ claim.submitted_at|date:"d M Y" }}){% endif %}.
            </p>

            <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                   style="background:#fff8ec; border-left:4px solid #fd7e14; border-radius:6px; margin:0 0 16px;">
              <tr>
                <td style="padding:14px 16px;">
                  <div style="font-size:12px; color:#8a4b08; font-weight:600;">Penalty amount</div>
                  <div style="font-size:22px; font-weight:700; color:#b02a37; margin-bottom:10px;">KES {{ penalty.amount|floatformat:2 }}</div>
                  <div style="font-size:12px; color:#8a4b08; font-weight:600;">Reason</div>
                  <div style="white-space:pre-line;">{{ penalty.reason }}</div>
                </td>
              </tr>
            </table>

            <p style="margin:0 0 16px;">
              This amount will be deducted from your <strong>next claim</strong>. It will appear there as
              a carry-forward advance, reducing the amount payable to you. Your {{ claim.month|date:"F Y" }}
              claim continues through review as normal.
            </p>

            {% if claim_url %}
            <p style="margin:0 0 8px;">
              <a href="{{ claim_url }}" style="display:inline-block; background:#123692; color:#ffffff; text-decoration:none; padding:10px 20px; border-radius:6px; font-weight:600;">View claim</a>
            </p>
            {% endif %}
          </td>
        </tr>
        <tr>
          <td style="padding:14px 24px; background:#f8f9fa; color:#6c757d; font-size:12px;">
            If you have questions about this penalty, please contact your manager.
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


def _notify_penalized(penalty, request=None):
    """
    Email the employee that their claim was penalized, by how much and why.

    Unlike _send_claim_email this does NOT swallow errors: it returns
    (sent: bool, problem: str) so the manager is told if the email failed.
    """
    import logging
    from django.core.mail import EmailMultiAlternatives
    from django.template import Template, Context
    from django.template.loader import get_template
    from django.template.exceptions import TemplateDoesNotExist
    from django.utils.html import strip_tags

    log = logging.getLogger(__name__)
    claim = penalty.claim
    employee = penalty.employee

    if not employee or not (employee.email or '').strip():
        return False, "the employee has no email address on their account"

    context = {
        'claim': claim,
        'penalty': penalty,
        'recipient_name': employee.get_full_name() or employee.username,
        'penalized_by_name': (
            penalty.penalized_by.get_full_name() or penalty.penalized_by.username
        ) if penalty.penalized_by else 'Your manager',
        'claim_url': _build_claim_url(request, claim) if request else '',
    }
    try:
        html_body = get_template('email/claim_penalized_email.html').render(context)
    except TemplateDoesNotExist:
        log.warning("email/claim_penalized_email.html not found; using built-in penalty email")
        html_body = Template(_PENALTY_EMAIL_FALLBACK).render(Context(context))

    text_body = (
        f"Hi {context['recipient_name']},\n\n"
        f"{context['penalized_by_name']} has placed a penalty of KES {penalty.amount:,.2f} on your "
        f"{claim.month.strftime('%B %Y')} claim.\n\n"
        f"Reason: {penalty.reason}\n\n"
        f"This amount will be deducted from your next claim.\n"
        + (f"\nView the claim: {context['claim_url']}\n" if context['claim_url'] else '')
    )
    try:
        msg = EmailMultiAlternatives(
            subject=f"[BRITS] Penalty on your claim — {claim.month.strftime('%B %Y')}",
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[employee.email.strip()],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=False)
        return True, ''
    except Exception as exc:
        log.exception("Penalty email to %s failed", employee.email)
        return False, f"the mail server returned an error ({exc.__class__.__name__}: {exc})"


# ─── Penalties: carried into the employee's next claim ────────────────────────

def _pending_penalties(employee, exclude_claim_pk=None):
    """Penalties not yet deducted from any claim. A claim never absorbs its own penalty."""
    qs = ClaimPenalty.objects.filter(employee=employee, applied_to_claim__isnull=True)
    if exclude_claim_pk:
        qs = qs.exclude(claim_id=exclude_claim_pk)
    return qs


def _apply_pending_penalties(claim):
    """
    Add the employee's outstanding penalties to this claim's carry_forward —
    the same field an overpayment carries forward through — and mark them as
    applied to this claim. Returns the total applied.
    """
    with transaction.atomic():
        pending = list(
            _pending_penalties(claim.employee, exclude_claim_pk=claim.pk).select_for_update()
        )
        total = sum((p.amount for p in pending), Decimal('0.00'))
        if not pending:
            return total
        claim.carry_forward = (claim.carry_forward or Decimal('0.00')) + total
        claim.save(update_fields=['carry_forward'])
        ClaimPenalty.objects.filter(pk__in=[p.pk for p in pending]).update(
            applied_to_claim=claim, applied_at=timezone.now()
        )
    return total


def _sum_amounts(qs):
    return qs.aggregate(s=Sum('amount'))['s'] or Decimal('0.00')


# ── Shims — keep existing call sites working ──────────────────────────────────

def _notify_next_approver(claim, request=None):
    """
    Called after submit (→ manager) or after manager approval (→ finance).
    Routes to the correct helper based on claim status.
    """
    if claim.status == ClaimForm.STATUS_SUBMITTED:
        _notify_submitted(claim, request)
    elif claim.status == ClaimForm.STATUS_MANAGER_APPROVED:
        _notify_manager_actioned(claim, request)


def _notify_employee_outcome(claim, request=None):
    """
    Called after finance approves or after any rejection.
    - Finance approved or finance rejected → _notify_finance_outcome (employee gets finance email)
    - Manager rejected → _notify_manager_actioned (employee gets manager-actioned email)
    Distinguish manager vs finance rejection by checking finance_actioned_at.
    """
    if claim.status == ClaimForm.STATUS_FINANCE_APPROVED:
        _notify_finance_outcome(claim, request)
    elif claim.status == ClaimForm.STATUS_REJECTED:
        if claim.finance_actioned_at:
            # Rejected at Finance stage
            _notify_finance_outcome(claim, request)
        else:
            # Rejected at Manager stage
            _notify_manager_actioned(claim, request)


# ─── Claim list ────────────────────────────────────────────────────────────────

def _filtered_claims(request, params):
    """
    The claim list's visibility rules + search/status/employee/date filters.
    Moved verbatim out of claim_list() so the list page and the bulk export
    always select exactly the same claims. `params` is a QueryDict
    (request.GET for the list page).
    Returns (queryset, filter_values).
    """
    user = request.user
    elevated = _is_elevated(user)

    """if elevated:
        all_claims_qs = ClaimForm.objects.select_related('employee', 'manager', 'finance_reviewer')
    else:
        all_claims_qs = ClaimForm.objects.filter(
            employee=user
        ).select_related('employee', 'manager', 'finance_reviewer')"""

    if elevated:
        all_claims_qs = ClaimForm.objects.select_related(
            'employee', 'manager', 'finance_reviewer'
        ).filter(
            ~Q(status=ClaimForm.STATUS_DRAFT) | Q(employee=user)
        )
    else:
        all_claims_qs = ClaimForm.objects.filter(
            employee=user
        ).select_related('employee', 'manager', 'finance_reviewer')

    search = params.get('q', '').strip()
    status_filter = params.get('status', '').strip()
    employee_filter = params.get('emp', '').strip()

    if search:
        all_claims_qs = all_claims_qs.filter(
            Q(title__icontains=search) |
            Q(employee__first_name__icontains=search) |
            Q(employee__last_name__icontains=search)
        )
    if status_filter:
        all_claims_qs = all_claims_qs.filter(status=status_filter)
    if employee_filter and elevated:
        all_claims_qs = all_claims_qs.filter(employee__id=employee_filter)

    # ── Date filters: submission date & closed (finance-actioned) date ──────
    # Additive only — none of the filtering logic above is touched.
    submitted_from = params.get('submitted_from', '').strip()
    submitted_to = params.get('submitted_to', '').strip()
    closed_from = params.get('closed_from', '').strip()
    closed_to = params.get('closed_to', '').strip()

    def _parse_date(value):
        from datetime import datetime as _dt
        try:
            return _dt.strptime(value, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return None

    submitted_from_date = _parse_date(submitted_from)
    submitted_to_date = _parse_date(submitted_to)
    closed_from_date = _parse_date(closed_from)
    closed_to_date = _parse_date(closed_to)

    if submitted_from_date:
        all_claims_qs = all_claims_qs.filter(submitted_at__date__gte=submitted_from_date)
    if submitted_to_date:
        all_claims_qs = all_claims_qs.filter(submitted_at__date__lte=submitted_to_date)
    # "Closed" = the claim reached the terminal finance_actioned_at stamp
    # (finance_approved status, tracked via finance_actioned_at).
    if closed_from_date:
        all_claims_qs = all_claims_qs.filter(finance_actioned_at__date__gte=closed_from_date)
    if closed_to_date:
        all_claims_qs = all_claims_qs.filter(finance_actioned_at__date__lte=closed_to_date)

    filter_values = {
        'search': search,
        'status_filter': status_filter,
        'employee_filter': employee_filter,
        'submitted_from': submitted_from,
        'submitted_to': submitted_to,
        'closed_from': closed_from,
        'closed_to': closed_to,
    }
    return all_claims_qs, filter_values


@login_required
def claim_list(request):
    user = request.user
    elevated = _is_elevated(user)

    all_claims_qs, _f = _filtered_claims(request, request.GET)
    search = _f['search']
    status_filter = _f['status_filter']
    employee_filter = _f['employee_filter']
    submitted_from = _f['submitted_from']
    submitted_to = _f['submitted_to']
    closed_from = _f['closed_from']
    closed_to = _f['closed_to']

    # Employees list to populate the "Employee" filter dropdown (elevated only).
    # The `emp` GET param and its filter above already existed and worked —
    # this just adds the missing UI control for it.
    employees_for_filter = []
    if elevated:
        employees_for_filter = User.objects.filter(
            claim_forms__isnull=False
        ).distinct().order_by('first_name', 'last_name')

    pending_approvals = ClaimForm.objects.filter(
        Q(manager=user, status=ClaimForm.STATUS_SUBMITTED) |
        Q(finance_reviewer=user, status=ClaimForm.STATUS_PENDING_DISBURSEMENT)
    ).select_related('employee')

    paginator = Paginator(all_claims_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    summary = None
    if elevated:
        summary = {
            'total': all_claims_qs.count(),
            'pending': all_claims_qs.filter(
                status__in=[
                    ClaimForm.STATUS_SUBMITTED,
                    ClaimForm.STATUS_MANAGER_APPROVED,
                    ClaimForm.STATUS_PENDING_DISBURSEMENT,
                ]
            ).count(),
            'approved': all_claims_qs.filter(status=ClaimForm.STATUS_FINANCE_APPROVED).count(),
            'rejected': all_claims_qs.filter(status=ClaimForm.STATUS_REJECTED).count(),
            'total_paid': all_claims_qs.filter(
                status=ClaimForm.STATUS_FINANCE_APPROVED
            ).aggregate(s=Sum('amount_paid'))['s'] or 0,
        }

    context = {
        'page_obj': page_obj,
        'pending_approvals': pending_approvals,
        'page_title': 'All Claims' if elevated else 'My Claims',
        'elevated': elevated,
        'can_delete': _can_delete(user),
        'summary': summary,
        'search': search,
        'status_filter': status_filter,
        'status_choices': ClaimForm.STATUS_CHOICES,
        'can_view_logs': user.has_perm('core.view_fileaccesslog'),
        # ── New filter context (additive) ──
        'employee_filter': employee_filter,
        'employees_for_filter': employees_for_filter,
        'submitted_from': submitted_from,
        'submitted_to': submitted_to,
        'closed_from': closed_from,
        'closed_to': closed_to,
        # ── Bulk export context (additive) ──
        'filter_querystring': _filter_querystring(request.GET),
        'bulk_export_limit': BULK_EXPORT_LIMIT,
        # ── One-open-claim rule (additive) ──
        'open_claim': _open_claim_for(user),
    }
    return render(request, 'core/claims/claim_list.html', context)


def _penalty_form_context(employee, carry_amount, claim=None, applied_total=Decimal('0.00')):
    """
    Template values for showing penalty deductions on the claim form.
      penalty_total        — penalties this claim carries (applied + about to apply)
      carry_forward_total  — carry-forward + penalties, used for the live net total
    """
    pending = _pending_penalties(employee, exclude_claim_pk=claim.pk if claim else None)
    pending_total = _sum_amounts(pending)
    penalty_total = applied_total + pending_total
    return {
        'penalty_total': penalty_total,
        'pending_penalties': pending.select_related('claim'),
        'applied_penalties': claim.applied_penalties.select_related('claim') if claim else [],
        'carry_forward_total': (carry_amount or Decimal('0.00')) + penalty_total,
    }


# ─── Create / Edit ─────────────────────────────────────────────────────────────
@login_required
def claim_create(request):
    user = request.user

    # One open claim at a time: no new claim until the current one is closed.
    open_claim = _open_claim_for(user)
    if open_claim:
        messages.warning(request, _open_claim_message(open_claim))
        return redirect('claim_detail', pk=open_claim.pk)

    # Default carry-forward values
    prev_claim_ref = None
    carry_amount = Decimal('0.00')

    if request.method == 'POST':

        form = ClaimFormForm(request.POST)
        formset = ClaimEntryFormSet(request.POST)

        if form.is_valid() and formset.is_valid():

            claim = form.save(commit=False)
            claim.employee = user

            # Auto title
            claim.title = claim.get_auto_title()

            # Compute carry-forward AFTER month exists
            prev_claim_ref, carry_amount = claim.compute_carry_forward()

            if prev_claim_ref:
                claim.carry_forward = carry_amount
                claim.previous_claim = prev_claim_ref

            claim.save()

            formset.instance = claim
            formset.save()

            # Outstanding penalties are deducted from this (the next) claim
            _apply_pending_penalties(claim)

            action = request.POST.get('action', 'save')

            if action == 'submit':
                claim.status = ClaimForm.STATUS_SUBMITTED
                claim.submitted_at = timezone.now()
                claim.save()

                _notify_next_approver(claim, request)

                messages.success(request, "Claim submitted for manager approval.")
            else:
                messages.success(request, "Claim saved as draft.")

            return redirect('claim_detail', pk=claim.pk)


    else:
        from datetime import date as _date
        today = _date.today()
        auto_month = _date(today.year, today.month, 1)
        form = ClaimFormForm(
            initial={'advance': Decimal('0.00'), 'month': auto_month}
        )
        formset = ClaimEntryFormSet()

        # Show carry-forward preview for new claims
        class _TempClaim:
            employee = user
            month = auto_month
            pk = None

            def get_latest_approved_claim(self_):
                return (
                    ClaimForm.objects.filter(
                        employee=user,
                        status=ClaimForm.STATUS_FINANCE_APPROVED,
                    )
                    .order_by('-month', '-finance_actioned_at')
                    .first()
                )

            def compute_carry_forward(self_):
                prev = self_.get_latest_approved_claim()
                if prev is None:
                    return None, Decimal('0.00')
                return prev, prev.balance_due

        tmp = _TempClaim()
        prev_claim_ref, carry_amount = tmp.compute_carry_forward()

    return render(request, 'core/claims/claim_form.html', {
        'form': form,
        'formset': formset,
        'page_title': 'New Claim',
        'is_new': True,
        'prev_claim_ref': prev_claim_ref,
        'carry_amount': carry_amount,
        **_penalty_form_context(user, carry_amount),
        'can_view_logs': user.has_perm('core.view_fileaccesslog'),
    })


@login_required
def claim_edit(request, pk):
    claim = get_object_or_404(ClaimForm, pk=pk, employee=request.user)
    editable_statuses = (
        ClaimForm.STATUS_DRAFT,
        ClaimForm.STATUS_REJECTED,
    )
    if claim.status not in editable_statuses:
        messages.error(request, "Only draft or rejected claims can be edited.")
        return redirect('claim_detail', pk=pk)

    if request.method == 'POST':
        form = ClaimFormForm(request.POST, instance=claim)
        formset = ClaimEntryFormSet(request.POST, instance=claim)
        if form.is_valid() and formset.is_valid():
            claim = form.save(commit=False)
            claim.title = claim.get_auto_title()
            claim.save()
            formset.save()
            action = request.POST.get('action', 'save')
            blocking_claim = _open_claim_for(request.user, exclude_pk=claim.pk) if action == 'submit' else None
            if blocking_claim:
                messages.warning(
                    request,
                    "Your changes were saved, but the claim was not submitted. "
                    + _open_claim_message(blocking_claim)
                )
            elif action == 'submit':
                _apply_pending_penalties(claim)
                claim.status = ClaimForm.STATUS_SUBMITTED
                claim.submitted_at = timezone.now()
                claim.save()
                _notify_next_approver(claim, request)
                messages.success(request, "Claim re-submitted for approval.")
            else:
                messages.success(request, "Claim updated.")
            return redirect('claim_detail', pk=pk)

    else:
        form = ClaimFormForm(instance=claim)
        formset = ClaimEntryFormSet(instance=claim)

    prev_claim_ref = claim.previous_claim
    # Display only: show penalties already folded into carry_forward on their
    # own line, so the carry-forward line shows just the previous balance.
    applied_penalty_total = _sum_amounts(claim.applied_penalties.all())
    carry_amount = claim.carry_forward - applied_penalty_total

    return render(request, 'core/claims/claim_form.html', {
        'form': form,
        'formset': formset,
        'claim': claim,
        'page_title': 'Edit Claim',
        'is_new': False,
        'blocking_claim': _open_claim_for(request.user, exclude_pk=claim.pk),
        'prev_claim_ref': prev_claim_ref,
        'carry_amount': carry_amount,
        **_penalty_form_context(claim.employee, carry_amount, claim=claim,
                                applied_total=applied_penalty_total),
        'can_view_logs': request.user.has_perm('core.view_fileaccesslog'),
    })


# ─── Detail ────────────────────────────────────────────────────────────────────
@login_required
def claim_detail(request, pk):
    claim = get_object_or_404(
        ClaimForm.objects.select_related('employee', 'manager', 'finance_reviewer')
                         .prefetch_related('entries', 'payment_records__recorded_by'),
        pk=pk
    )

    user = request.user
    elevated = _is_elevated(user)
    is_finance_user = _is_finance(user)

    if claim.status == ClaimForm.STATUS_DRAFT and user != claim.employee:
        messages.error(request, "You do not have access to this claim.")
        return redirect('claim_list')

    allowed = [claim.employee, claim.manager, claim.finance_reviewer]

    if user not in allowed and not elevated:
        messages.error(request, "You do not have access to this claim.")
        return redirect('claim_list')

    prev_claim = claim.get_previous_claim()
    #claim_history = claim.get_claim_history()[:5]
    claim_history_qs = claim.get_claim_history()
    history_paginator = Paginator(claim_history_qs, 5)
    history_page_obj = history_paginator.get_page(request.GET.get('history_page'))

    # ── Finance Actions — two stages ─────────────────────────────────────────────
    # Stage 1 (manager, status = manager_approved): manager records the amount
    #   they recommend Finance disburse ("Amount Suggested"). This forwards the
    #   claim to Finance (status -> pending_disbursement). No money is marked
    #   as paid and the claim is not closed.
    # Stage 2 (finance, status = pending_disbursement): finance reviews /
    #   edits the suggested amount and records the final payment. This creates
    #   the official PaymentRecord, marks the claim Closed, and redirects back
    #   to the claim list.
    suggestion_form = None
    payment_form = None
    payment_records = claim.payment_records.all()

    can_suggest_amount = (
        claim.status == ClaimForm.STATUS_MANAGER_APPROVED
        and (claim.manager == user or elevated)
    )
    can_record_payment = (
        claim.status == ClaimForm.STATUS_PENDING_DISBURSEMENT
        and (claim.finance_reviewer == user or _is_finance_strict(user))
    )

    if can_suggest_amount and request.method == 'POST' and 'record_suggestion' in request.POST:
        suggestion_form = SuggestedAmountForm(request.POST, instance=claim)
        if suggestion_form.is_valid():
            amount = suggestion_form.cleaned_data['suggested_amount']
            claim.record_suggestion(user, amount)
            messages.success(
                request,
                f"Suggested amount of KES {amount:,.2f} recorded. "
                f"Claim forwarded to Finance for payment."
            )
            return redirect('claim_detail', pk=pk)
    elif can_suggest_amount:
        suggestion_form = SuggestedAmountForm()

    if can_record_payment and request.method == 'POST' and 'record_payment' in request.POST:
        payment_form = PaymentRecordForm(request.POST)
        if payment_form.is_valid():
            record = payment_form.save(commit=False)
            record.claim = claim
            record.recorded_by = user
            record.paid_at = timezone.now()
            record.save()  # triggers claim.refresh_amount_paid() automatically

            claim.refresh_from_db()
            claim.status = ClaimForm.STATUS_FINANCE_APPROVED
            claim.finance_actioned_at = timezone.now()
            claim.save()

            _notify_employee_outcome(claim, request)

            overpayment = claim.overpayment
            if overpayment > Decimal('0.00'):
                messages.warning(
                    request,
                    f"⚠️ Payment of KES {record.amount:,.2f} recorded and the claim is now closed. "
                    f"This exceeds the net payable by KES {overpayment:,.2f}. "
                    f"The surplus will automatically be deducted from "
                    f"{claim.employee.get_full_name()}'s next claim as a carry-forward advance."
                )
            else:
                messages.success(
                    request,
                    f"Payment of KES {record.amount:,.2f} recorded. Claim closed."
                )

            return redirect('claim_list')
    elif can_record_payment:
        initial = {}
        if claim.suggested_amount:
            initial['amount'] = claim.suggested_amount
        payment_form = PaymentRecordForm(initial=initial)

    return render(request, 'core/claims/claim_detail.html', {
        'claim': claim,
        'entries': claim.entries.all(),
        'approval_form': ApprovalActionForm(),
        'can_approve': claim.can_approve(user),
        'page_title': f"Claim — {claim.employee.get_full_name()}",
        'can_view_logs': user.has_perm('core.view_fileaccesslog'),
        'elevated': elevated,
        'is_finance_user': is_finance_user,
        'can_delete': _can_delete(user),
        'prev_claim': prev_claim,
        #'claim_history': claim_history,
        'claim_history': history_page_obj,
        'history_page_obj': history_page_obj,
        'suggestion_form': suggestion_form,
        'can_suggest_amount': can_suggest_amount,
        'payment_form': payment_form,
        'payment_records': payment_records,
        # ── Penalties (additive) ──
        'penalties': claim.penalties.select_related('penalized_by', 'applied_to_claim'),
        'applied_penalties': claim.applied_penalties.select_related('claim'),
        'applied_penalty_total': _sum_amounts(claim.applied_penalties.all()),
        'can_record_payment': can_record_payment,
        'can_view_payment_log': elevated or is_finance_user or claim.finance_reviewer == user,
    })

def _is_finance_strict(user):
    if user.is_superuser:
        return True
    role = getattr(user, 'role', '').lower() if hasattr(user, 'role') else ''
    if role in ('finance', 'director'):   # 'manager' removed
        return True
    return user.groups.filter(name__in=['Finance', 'Director', 'Superadmin']).exists()

# ─── Approval ──────────────────────────────────────────────────────────────────

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
        _notify_next_approver(claim, request)
        # Only notify the employee when Finance is the final approver
        if claim.status == ClaimForm.STATUS_FINANCE_APPROVED:
            _notify_employee_outcome(claim, request)
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
        _notify_employee_outcome(claim, request)
        messages.warning(request, "Claim rejected. Employee has been notified.")
    return redirect('claim_detail', pk=pk)


@login_required
def claim_penalize(request, pk):
    """
    Manager penalizes a claim under review. Same permission as approve/reject.
    The claim's status does NOT change — the manager can still approve or
    reject it. The amount is deducted from the employee's next claim.
    """
    if request.method != 'POST':
        return redirect('claim_detail', pk=pk)
    claim = get_object_or_404(ClaimForm, pk=pk)
    if not claim.can_approve(request.user):
        messages.error(request, "You are not authorised to penalize this claim.")
        return redirect('claim_detail', pk=pk)

    form = PenaltyForm(request.POST)
    if not form.is_valid():
        errors = '; '.join(e for errs in form.errors.values() for e in errs)
        messages.error(request, f"Penalty not recorded: {errors}")
        return redirect('claim_detail', pk=pk)

    penalty = form.save(commit=False)
    penalty.claim = claim
    penalty.employee = claim.employee
    penalty.penalized_by = request.user
    penalty.save()

    sent, problem = _notify_penalized(penalty, request)
    if sent:
        messages.success(
            request,
            f"Penalty of KES {penalty.amount:,.2f} recorded. It will be deducted from "
            f"{claim.employee.get_full_name()}'s next claim, and they have been notified by email."
        )
    else:
        messages.warning(
            request,
            f"Penalty of KES {penalty.amount:,.2f} recorded and will be deducted from "
            f"{claim.employee.get_full_name()}'s next claim, but the email could NOT be sent: {problem}."
        )
    return redirect('claim_detail', pk=pk)


# ─── Delete ────────────────────────────────────────────────────────────────────

@login_required
def claim_delete(request, pk):
    if not _can_delete(request.user):
        messages.error(request, "You do not have permission to delete claims.")
        return redirect('claim_detail', pk=pk)
    claim = get_object_or_404(ClaimForm, pk=pk)
    if request.method == 'POST':
        employee_name = claim.employee.get_full_name()
        month_label = claim.month.strftime('%B %Y')
        claim.delete()
        messages.success(request, f"Claim for {employee_name} ({month_label}) has been deleted.")
        return redirect('claim_list')
    return redirect('claim_detail', pk=pk)


# ─── Export ────────────────────────────────────────────────────────────────────

BULK_EXPORT_LIMIT = 200   # max claims per bulk download (PDF rendering is slow)


def _local_dt(dt):
    """Convert to local time when timezone-aware; pass naive values through."""
    if dt is None:
        return None
    return timezone.localtime(dt) if timezone.is_aware(dt) else dt


def _naive_local(dt):
    """Local, tz-stripped datetime (openpyxl cannot store aware datetimes)."""
    dt = _local_dt(dt)
    return dt.replace(tzinfo=None) if dt else None


def _safe_name(value, fallback='claim'):
    try:
        return get_valid_filename(value) or fallback
    except Exception:
        return fallback


def _claim_export_filename(claim, ext):
    """
    e.g. claim_Jane_Wanjiru_2026_10_submitted_2026-10-14.pdf
    The covered month stays in the name (as before); the exact submission
    date is appended so downloads sort and track easily.
    """
    name = _safe_name(claim.employee.get_full_name() or claim.employee.username)
    submitted = _local_dt(claim.submitted_at)
    stamp = f"submitted_{submitted:%Y-%m-%d}" if submitted else "not-submitted"
    return f"claim_{name}_{claim.month.strftime('%Y_%m')}_{stamp}.{ext}"


def _filter_querystring(params):
    """Current list filters as a querystring, minus paging/format keys."""
    qd = params.copy()
    for key in ('page', 'format'):
        qd.pop(key, None)
    return qd.urlencode()


def _can_export_claim(user, claim, elevated):
    """Same access rule the single-claim PDF/Excel exports enforce."""
    if claim.status == ClaimForm.STATUS_DRAFT and user != claim.employee:
        return False
    allowed = [claim.employee, claim.manager, claim.finance_reviewer]
    return user in allowed or elevated


def _render_claim_pdf_bytes(claim, request):
    """Render one claim with the same template/engine as claim_export_pdf."""
    from weasyprint import HTML
    html_string = render_to_string('core/claims/claim_pdf.html', {'claim': claim})
    return HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()


def _bulk_label(filters, selected_count=None):
    """Describes the group in the ZIP / register filename."""
    if selected_count is not None:
        return f"selected_{selected_count}_{date.today():%Y-%m-%d}"
    parts = []
    for key, prefix in (('submitted', 'submitted'), ('closed', 'closed')):
        start, end = filters.get(f'{key}_from'), filters.get(f'{key}_to')
        if start or end:
            parts.append(f"{prefix}_{start or 'start'}_to_{end or 'now'}")
    if filters.get('status_filter'):
        parts.append(filters['status_filter'])
    return '_'.join(parts) or f"all_{date.today():%Y-%m-%d}"


def _build_claims_register(claims, heading):
    """
    One-workbook summary of a group of claims: a 'Claims' sheet with one row
    per claim (all key dates + amounts) and a 'By Month' sheet grouping them
    by submission month. Returns xlsx bytes.
    """
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter

    thin = Side(style='thin')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    navy_fill = PatternFill("solid", fgColor="1F3864")
    navy_font = Font(bold=True, color="FFFFFF")
    bold = Font(bold=True)
    money = '#,##0.00'

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Claims"

    headers = [
        ('Claim ID', 9), ('Employee', 24), ('Title', 26), ('Month Covered', 14),
        ('Status', 20), ('Submitted', 18), ('Manager Actioned', 18), ('Closed', 18),
        ('Manager', 20), ('Finance Reviewer', 20),
        ('Sub-total', 13), ('Advance', 12), ('Carry-forward', 13),
        ('Total Minus Advance', 16), ('Suggested', 13), ('Amount Paid', 13),
        ('Balance Due', 13),
    ]
    ncols = len(headers)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    ws['A1'] = heading
    ws['A1'].font = Font(bold=True, size=13)
    ws.row_dimensions[1].height = 24

    for col, (label, width) in enumerate(headers, start=1):
        c = ws.cell(row=2, column=col, value=label)
        c.font, c.fill, c.border = navy_font, navy_fill, border
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.freeze_panes = 'C3'

    money_cols = range(11, 18)
    date_cols = (6, 7, 8)
    totals = {k: Decimal('0.00') for k in ('subtotal', 'advance', 'paid')}
    by_month = {}

    row = 3
    for claim in claims:
        is_closed = claim.status == ClaimForm.STATUS_FINANCE_APPROVED
        closed_at = claim.finance_actioned_at if is_closed else None
        subtotal = claim.subtotal
        values = [
            claim.pk,
            claim.employee.get_full_name() or claim.employee.username,
            claim.display_title,
            claim.month.strftime('%B %Y'),
            claim.get_status_display(),
            _naive_local(claim.submitted_at),
            _naive_local(claim.manager_actioned_at),
            _naive_local(closed_at),
            claim.manager.get_full_name() if claim.manager else '',
            claim.finance_reviewer.get_full_name() if claim.finance_reviewer else '',
            float(subtotal), float(claim.advance), float(claim.carry_forward),
            float(claim.total_minus_advance),
            float(claim.suggested_amount) if claim.suggested_amount is not None else None,
            float(claim.amount_paid), float(claim.balance_due),
        ]
        for col, val in enumerate(values, start=1):
            c = ws.cell(row=row, column=col, value=val)
            c.border = border
            if col in date_cols and val:
                c.number_format = 'DD/MM/YYYY HH:MM'
            elif col in money_cols:
                c.number_format = money
        totals['subtotal'] += subtotal
        totals['advance'] += claim.advance
        totals['paid'] += claim.amount_paid

        sub = _local_dt(claim.submitted_at)
        key = sub.strftime('%Y-%m') if sub else 'Not submitted'
        g = by_month.setdefault(key, {'count': 0, 'closed': 0, 'subtotal': Decimal('0.00'), 'paid': Decimal('0.00')})
        g['count'] += 1
        g['closed'] += 1 if is_closed else 0
        g['subtotal'] += subtotal
        g['paid'] += claim.amount_paid
        row += 1

    ws.cell(row=row, column=1, value=f"Totals ({len(claims)} claim{'' if len(claims) == 1 else 's'})").font = bold
    for col, key in ((11, 'subtotal'), (12, 'advance'), (16, 'paid')):
        c = ws.cell(row=row, column=col, value=float(totals[key]))
        c.font, c.number_format = bold, money

    ws2 = wb.create_sheet("By Month")
    for col, (label, width) in enumerate(
        [('Submitted Month', 18), ('Claims', 10), ('Closed', 10), ('Sub-total', 15), ('Amount Paid', 15)], start=1
    ):
        c = ws2.cell(row=1, column=col, value=label)
        c.font, c.fill, c.border = navy_font, navy_fill, border
        ws2.column_dimensions[get_column_letter(col)].width = width
    for r, key in enumerate(sorted(by_month, reverse=True), start=2):
        g = by_month[key]
        label = datetime.strptime(key, '%Y-%m').strftime('%B %Y') if key[:1].isdigit() else key
        for col, val in enumerate([label, g['count'], g['closed'], float(g['subtotal']), float(g['paid'])], start=1):
            c = ws2.cell(row=r, column=col, value=val)
            c.border = border
            if col >= 4:
                c.number_format = money

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


@login_required
def claim_bulk_export(request):
    """
    Download a group of claims at once.

    GET  → every claim matching the list filters in the querystring
           (e.g. Submitted 01 Oct – 31 Oct), exactly as the list shows them.
    POST → only the claims ticked on the list page (`ids`).

    format=zip      → ZIP of each claim's PDF (dated filenames) + a register
    format=register → the Excel register only
    """
    user = request.user
    fmt = (request.POST.get('format') or request.GET.get('format') or 'zip').strip()
    list_url = reverse('claim_list')

    if request.method == 'POST':
        ids = [i for i in request.POST.getlist('ids') if i.isdigit()]
        back_qs = request.POST.get('back_qs', '')
        back = f"{list_url}?{back_qs}" if back_qs else list_url
        if not ids:
            messages.warning(request, "Tick at least one claim to download.")
            return redirect(back)
        # Start from the same visibility rules as the list, without filters
        qs, filters = _filtered_claims(request, QueryDict(''))
        qs = qs.filter(pk__in=ids)
        label = None   # set below, once we know how many claims are exportable
    else:
        qs, filters = _filtered_claims(request, request.GET)
        back_qs = _filter_querystring(request.GET)
        back = f"{list_url}?{back_qs}" if back_qs else list_url
        label = _bulk_label(filters)

    qs = qs.select_related('employee', 'manager', 'finance_reviewer') \
           .prefetch_related('entries', 'payment_records')

    total = qs.count()
    if total == 0:
        messages.warning(request, "No claims to download for that selection.")
        return redirect(back)
    if total > BULK_EXPORT_LIMIT:
        messages.error(
            request,
            f"That group has {total} claims; the bulk download limit is {BULK_EXPORT_LIMIT}. "
            f"Narrow the date range or filters and try again."
        )
        return redirect(back)

    elevated = _is_elevated(user)
    claims = [c for c in qs if _can_export_claim(user, c, elevated)]
    claims.sort(key=lambda c: (c.submitted_at is None, c.submitted_at or c.created_at))
    if label is None:
        label = _bulk_label(filters, selected_count=len(claims))
    heading = f"Claims register — {label.replace('_', ' ')}"

    if fmt == 'register':
        try:
            data = _build_claims_register(claims, heading)
        except ImportError:
            return HttpResponse("openpyxl is not installed. Run: pip install openpyxl", status=500)
        response = HttpResponse(
            data, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="claims_register_{_safe_name(label)}.xlsx"'
        return response

    # Default: ZIP of PDFs (+ register when openpyxl is available)
    try:
        import weasyprint  # noqa: F401
    except ImportError:
        return HttpResponse("WeasyPrint is not installed. Run: pip install weasyprint", status=500)

    buf = io.BytesIO()
    used_names = set()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for claim in claims:
            fname = _claim_export_filename(claim, 'pdf')
            if fname in used_names:                      # same person, month & day
                fname = fname[:-4] + f"_{claim.pk}.pdf"
            used_names.add(fname)
            zf.writestr(fname, _render_claim_pdf_bytes(claim, request))
        try:
            zf.writestr(f"_register_{_safe_name(label)}.xlsx", _build_claims_register(claims, heading))
        except ImportError:
            pass

    response = HttpResponse(buf.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="claims_{_safe_name(label)}.zip"'
    return response


@login_required
def claim_export_pdf(request, pk):
    claim = get_object_or_404(
        ClaimForm.objects.select_related('employee').prefetch_related('entries', 'payment_records'),
        pk=pk
    )
    if claim.status == ClaimForm.STATUS_DRAFT and request.user != claim.employee:
        return HttpResponse("Forbidden", status=403)
    allowed = [claim.employee, claim.manager, claim.finance_reviewer]
    if request.user not in allowed and not _is_elevated(request.user):
        return HttpResponse("Forbidden", status=403)
    try:
        from weasyprint import HTML
        html_string = render_to_string('core/claims/claim_pdf.html', {'claim': claim})
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        filename = _claim_export_filename(claim, 'pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except ImportError:
        return HttpResponse("WeasyPrint is not installed. Run: pip install weasyprint", status=500)

@login_required
def claim_export_excel(request, pk):
    claim = get_object_or_404(
        ClaimForm.objects.select_related('employee').prefetch_related('entries', 'payment_records'),
        pk=pk
    )
    if claim.status == ClaimForm.STATUS_DRAFT and request.user != claim.employee:
        return HttpResponse("Forbidden", status=403)
    allowed = [claim.employee, claim.manager, claim.finance_reviewer]
    if request.user not in allowed and not _is_elevated(request.user):
        return HttpResponse("Forbidden", status=403)
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Claim Form"

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

        ws.merge_cells('A1:M1')
        ws['A1'] = f"{claim.display_title.upper()} — {claim.month.strftime('%B %Y').upper()}"
        style_cell(ws['A1'], font=header_font, align=center)
        ws.row_dimensions[1].height = 28

        headers = ['DATE', 'SITE', 'TICKET NO.', 'TO', 'FROM',
           'BREAKFAST', 'LUNCH', 'DINNER', 'BED', 'OTHER EXPENDITURE', 'OTHER EXP. NOTE', 'TOTAL', 'ADVANCE']
        col_widths = [14, 22, 16, 10, 10, 12, 10, 10, 10, 16, 24, 12, 12]
        for col_idx, (h, w) in enumerate(zip(headers, col_widths), start=1):
            cell = ws.cell(row=2, column=col_idx, value=h)
            style_cell(cell, font=navy_font, align=center, fill=navy_fill, border_=border)
            ws.column_dimensions[get_column_letter(col_idx)].width = w
        ws.row_dimensions[2].height = 20

        NOTE_COL = 11  # 'OTHER EXP. NOTE' column — text, not currency

        for row_idx, entry in enumerate(claim.entries.all(), start=3):
            row_data = [
                entry.date, entry.site, entry.ticket_number,
                float(entry.transport_to), float(entry.transport_from),
                float(entry.breakfast), float(entry.lunch),
                float(entry.dinner), float(entry.bed), float(entry.other_expenditure),
                entry.other_expenditure_note,
                float(entry.total), '',
            ]
            for col_idx, val in enumerate(row_data, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.border = border
                if col_idx == 1:
                    cell.number_format = 'DD/MM/YYYY'
                    cell.alignment = center
                elif col_idx == NOTE_COL:
                    cell.alignment = Alignment(horizontal='left', wrap_text=True)
                elif col_idx >= 4:
                    cell.number_format = '#,##0.00'
                    cell.alignment = right

        last_data_row = 2 + claim.entries.count()
        subtotal_row = last_data_row + 2

        ws.merge_cells(f'A{subtotal_row}:K{subtotal_row}')
        ws.cell(subtotal_row, 1, 'Sub total').font = bold
        ws.cell(subtotal_row, 1).alignment = right
        ws.cell(subtotal_row, 12, float(claim.subtotal)).number_format = '#,##0.00'
        ws.cell(subtotal_row, 12).font = bold
        ws.cell(subtotal_row, 13, float(claim.advance)).number_format = '#,##0.00'
        ws.cell(subtotal_row, 13).font = bold

        if claim.carry_forward:
            cf_row = subtotal_row + 1
            ws.merge_cells(f'A{cf_row}:K{cf_row}')
            ws.cell(cf_row, 1, 'Carry-forward from previous claim').font = bold
            ws.cell(cf_row, 1).alignment = right
            ws.cell(cf_row, 12, float(claim.carry_forward)).number_format = '#,##0.00'
            ws.cell(cf_row, 12).font = bold
            tma_row = cf_row + 1
        else:
            tma_row = subtotal_row + 1

        ws.merge_cells(f'A{tma_row}:K{tma_row}')
        ws.cell(tma_row, 1, 'Total Minus Advance').font = bold
        ws.cell(tma_row, 1).alignment = right
        ws.cell(tma_row, 12, float(claim.total_minus_advance)).number_format = '#,##0.00'
        ws.cell(tma_row, 12).font = bold

        pr_start = tma_row + 1
        for i, pr in enumerate(claim.payment_records.all()):
            pr_row = pr_start + i
            ws.merge_cells(f'A{pr_row}:K{pr_row}')
            label = f"Payment #{i+1} — {pr.paid_at.strftime('%d %b %Y')}"
            if pr.note:
                label += f" ({pr.note})"
            ws.cell(pr_row, 1, label).font = bold
            ws.cell(pr_row, 1).alignment = right
            ws.cell(pr_row, 12, float(pr.amount)).number_format = '#,##0.00'
            ws.cell(pr_row, 12).font = bold

        paid_row = pr_start + claim.payment_records.count()
        ws.merge_cells(f'A{paid_row}:K{paid_row}')
        ws.cell(paid_row, 1, 'Total Amount Paid').font = bold
        ws.cell(paid_row, 1).alignment = right
        ws.cell(paid_row, 12, float(claim.amount_paid)).number_format = '#,##0.00'
        ws.cell(paid_row, 12).font = bold

        if claim.overpayment > 0:
            op_row = paid_row + 1
            ws.merge_cells(f'A{op_row}:K{op_row}')
            ws.cell(op_row, 1, 'Overpayment (carry-forward to next claim)').font = bold
            ws.cell(op_row, 1).alignment = right
            ws.cell(op_row, 12, float(claim.overpayment)).number_format = '#,##0.00'
            ws.cell(op_row, 12).font = Font(bold=True, color='FF0000')
            sig_row = op_row + 3
        elif claim.balance_due < 0:
            # Negative balance_due = employer still owes employee
            bd_row = paid_row + 1
            ws.merge_cells(f'A{bd_row}:K{bd_row}')
            ws.cell(bd_row, 1, 'Outstanding Balance').font = bold
            ws.cell(bd_row, 1).alignment = right
            ws.cell(bd_row, 12, float(abs(claim.balance_due))).number_format = '#,##0.00'
            ws.cell(bd_row, 12).font = Font(bold=True, color='FF0000')
            sig_row = bd_row + 3
        else:
            sig_row = paid_row + 3

        ws.cell(sig_row, 1, 'EMPLOYEE SIGN').font = bold
        ws.cell(sig_row, 5, 'DATE').font = bold
        ws.cell(sig_row + 1, 1, 'MANAGER SIGN').font = bold
        ws.cell(sig_row + 1, 5, 'DATE').font = bold
        ws.cell(sig_row + 2, 1, 'FINANCE SIGN').font = bold
        ws.cell(sig_row + 2, 5, 'DATE').font = bold

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = _claim_export_filename(claim, 'xlsx')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        return response

    except ImportError:
        return HttpResponse("openpyxl is not installed. Run: pip install openpyxl", status=500)