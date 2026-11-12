from datetime import date

from django import forms
from django.contrib.auth import get_user_model

from .models import LeaveApplication, NOTICE_DAYS, NOTICE_EXEMPT_TYPES, count_working_days

User = get_user_model()


def _manager_queryset(exclude_user=None):
    """Same approver pool as claims: active Managers / Directors."""
    qs = User.objects.filter(
        is_active=True,
        is_superuser=False,
        is_staff=False,
        groups__name__in=['Manager', 'Director'],
    ).distinct().order_by('first_name', 'last_name')
    if exclude_user is not None:
        qs = qs.exclude(pk=exclude_user.pk)   # nobody approves their own leave
    return qs


class LeaveApplicationForm(forms.ModelForm):
    """
    Employee's leave application — mirrors the BRTS paper form.

    Pass `employee` (the applicant) and `submitting=True` when the user clicked
    Submit: the two-day notice rule and the overlap check only apply then, so
    an incomplete plan can still be saved as a draft.
    """

    class Meta:
        model = LeaveApplication
        fields = [
            'employee_number', 'leave_type', 'other_type_detail',
            'start_date', 'end_date', 'reason', 'manager',
        ]
        widgets = {
            'employee_number': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. BRTS-0042', 'maxlength': '50',
            }),
            'leave_type': forms.RadioSelect(attrs={'class': 'leave-type-radio'}),
            'other_type_detail': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Describe the type of absence',
                'maxlength': '120',
            }),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
            'reason': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'Briefly explain the reason for your absence',
            }),
            'manager': forms.Select(attrs={'class': 'form-select form-control'}),
        }
        labels = {
            'employee_number': 'Employee Number',
            'leave_type': 'Type of Absence Requested',
            'other_type_detail': 'Other — please specify',
            'start_date': 'From',
            'end_date': 'To',
            'reason': 'Reason for Absence',
            'manager': 'Approving Manager',
        }

    def __init__(self, *args, employee=None, submitting=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.employee = employee
        self.submitting = submitting
        self.fields['manager'].queryset = _manager_queryset(exclude_user=employee)
        self.fields['manager'].required = True
        self.fields['manager'].empty_label = 'Select your manager'
        self.fields['manager'].label_from_instance = lambda u: u.get_full_name() or u.username
        self.fields['leave_type'].choices = LeaveApplication.TYPE_CHOICES  # no blank radio
        self.fields['reason'].required = True
        self.fields['employee_number'].required = True
        self.fields['other_type_detail'].required = False

    def clean(self):
        cleaned = super().clean()
        leave_type = cleaned.get('leave_type')
        start = cleaned.get('start_date')
        end = cleaned.get('end_date')

        if leave_type == LeaveApplication.TYPE_OTHER and not (cleaned.get('other_type_detail') or '').strip():
            self.add_error('other_type_detail', "Please specify the type of absence.")

        if start and end:
            if end < start:
                self.add_error('end_date', "The end date cannot be before the start date.")
            elif count_working_days(start, end) == 0:
                self.add_error('end_date', "The selected dates fall entirely on a weekend.")

        if self.submitting and start and end and end >= start:
            # Two-day notice rule (from the paper form)
            if leave_type and leave_type not in NOTICE_EXEMPT_TYPES:
                days_ahead = (start - date.today()).days
                if days_ahead < NOTICE_DAYS:
                    self.add_error(
                        'start_date',
                        f"Requests other than sick leave must be submitted at least "
                        f"{NOTICE_DAYS} days before the first day of absence."
                    )
            # No overlap with another pending or approved application
            if self.employee is not None:
                clash = LeaveApplication.objects.filter(
                    employee=self.employee,
                    status__in=[LeaveApplication.STATUS_SUBMITTED, LeaveApplication.STATUS_APPROVED],
                    start_date__lte=end,
                    end_date__gte=start,
                )
                if self.instance.pk:
                    clash = clash.exclude(pk=self.instance.pk)
                clash = clash.first()
                if clash:
                    raise forms.ValidationError(
                        f"These dates overlap your {clash.get_status_display().lower()} "
                        f"{clash.get_leave_type_display().lower()} leave "
                        f"({clash.start_date:%d %b} – {clash.end_date:%d %b %Y})."
                    )
        return cleaned

    def clean_reason(self):
        reason = (self.cleaned_data.get('reason') or '').strip()
        if not reason:
            raise forms.ValidationError("Please give a reason for the absence.")
        return reason


class LeaveDecisionForm(forms.Form):
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))
