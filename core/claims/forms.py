from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth import get_user_model
from .models import ClaimForm, ClaimEntry, PaymentRecord
from datetime import date

User = get_user_model()


class ClaimFormForm(forms.ModelForm):
    """
    Claim header form.
    - month is now HIDDEN — auto-set to the current month in the view.
    - advance is shown inside the entries formset area.
    - manager / finance_reviewer dropdowns show only Managers & Directors.
    """

    class Meta:
        model = ClaimForm
        fields = ['month', 'advance', 'manager', 'finance_reviewer']
        widgets = {
            # month rendered as hidden; view auto-sets it to today's month
            'month': forms.HiddenInput(),
            'advance': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm money-field',
                'min': '0', 'step': '0.01', 'placeholder': '0.00',
                'id': 'id_advance_field',
                'style': 'width:140px; text-align:right;',
            }),
            'manager': forms.Select(attrs={'class': 'form-select'}),
            'finance_reviewer': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Auto-default month to the 1st of the current month (new claims only)
        if not self.instance.pk and 'month' not in self.initial:
            today = date.today()
            self.initial['month'] = date(today.year, today.month, 1)

        # Restrict approval chain dropdowns to Managers / Directors / Superadmins
        try:
            from django.db.models import Q
            elevated_qs = User.objects.filter(is_active=True).filter(
                Q(role__iexact='manager') |
                Q(role__iexact='director') |
                Q(is_superuser=True)
            ).order_by('first_name', 'last_name')
        except Exception:
            from django.db.models import Q
            elevated_qs = User.objects.filter(is_active=True).filter(
                Q(groups__name__in=['Manager', 'Director', 'Superadmin']) |
                Q(is_superuser=True)
            ).distinct().order_by('first_name', 'last_name')

        self.fields['manager'].queryset = elevated_qs
        self.fields['finance_reviewer'].queryset = elevated_qs

    def clean_month(self):
        month = self.cleaned_data.get('month')
        if not month:
            today = date.today()
            return date(today.year, today.month, 1)
        if hasattr(month, 'year'):
            return date(month.year, month.month, 1)
        return month


class ClaimEntryForm(forms.ModelForm):
    class Meta:
        model = ClaimEntry
        fields = [
            'date', 'site', 'ticket_number', 'ticket_url',
            'transport_to', 'transport_from',
            'breakfast', 'lunch', 'dinner', 'bed', 'other_expenditure',
        ]
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date', 'class': 'form-control form-control-sm entry-date'
            }),
            'site': forms.TextInput(attrs={
                'class': 'form-control form-control-sm', 'placeholder': 'Site name'
            }),
            'ticket_number': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'e.g. TKT-1042'
            }),
            'ticket_url': forms.URLInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'https://... (optional)'
            }),
            'transport_to': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm money-field',
                'min': '0', 'step': '0.01', 'placeholder': '0'
            }),
            'transport_from': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm money-field',
                'min': '0', 'step': '0.01', 'placeholder': '0'
            }),
            'breakfast': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm money-field',
                'min': '0', 'step': '0.01', 'placeholder': '0'
            }),
            'lunch': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm money-field',
                'min': '0', 'step': '0.01', 'placeholder': '0'
            }),
            'dinner': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm money-field',
                'min': '0', 'step': '0.01', 'placeholder': '0'
            }),
            'bed': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm money-field',
                'min': '0', 'step': '0.01', 'placeholder': '0'
            }),
            'other_expenditure': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm money-field',
                'min': '0',
                'step': '0.01',
                'placeholder': '0',
            }),
        }


ClaimEntryFormSet = inlineformset_factory(
    ClaimForm,
    ClaimEntry,
    form=ClaimEntryForm,
    extra=10,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class ApprovalActionForm(forms.Form):
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional comment (required for rejection)'
        })
    )


class PaymentRecordForm(forms.ModelForm):
    """
    Finance records a single disbursement against a finance-approved claim.
    Replaces FinancePaymentForm — supports partial & multiple payments.
    """
    class Meta:
        model = PaymentRecord
        fields = ['amount', 'note']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0.01',
                'step': '0.01',
                'placeholder': '0.00',
            }),
            'note': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Full payment / Partial — balance pending (optional)',
                'maxlength': '255',
            }),
        }
        labels = {
            'amount': 'Amount Disbursed (KES)',
            'note': 'Note',
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        return amount


# Keep old name around so existing imports don't break immediately
FinancePaymentForm = PaymentRecordForm