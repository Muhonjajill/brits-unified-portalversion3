from django import forms
from django.forms import inlineformset_factory
from .models import ClaimForm, ClaimEntry


class ClaimFormForm(forms.ModelForm):
    month = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'month', 'class': 'form-control'}),
        input_formats=['%Y-%m'],
        help_text="Select the month for this claim"
    )

    class Meta:
        model = ClaimForm
        # HR reviewer removed from approval chain
        fields = ['title', 'month', 'advance', 'manager', 'finance_reviewer']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. April 2026 Field Claims'
            }),
            'advance': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '0', 'step': '0.01'
            }),
            'manager': forms.Select(attrs={'class': 'form-select'}),
            'finance_reviewer': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_month(self):
        month = self.cleaned_data['month']
        from datetime import date
        return date(month.year, month.month, 1)


class ClaimEntryForm(forms.ModelForm):
    class Meta:
        model = ClaimEntry
        fields = [
            'date', 'site', 'ticket_number', 'ticket_url',
            'transport_to', 'transport_from',
            'breakfast', 'lunch', 'dinner', 'bed',
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
        }


ClaimEntryFormSet = inlineformset_factory(
    ClaimForm,
    ClaimEntry,
    form=ClaimEntryForm,
    extra=5,
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


class FinancePaymentForm(forms.ModelForm):
    """Finance records the actual disbursement against a finance-approved claim."""
    class Meta:
        model = ClaimForm
        fields = ['amount_paid']
        widgets = {
            'amount_paid': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'placeholder': '0.00',
            })
        }
        labels = {'amount_paid': 'Amount Disbursed (KES)'}
