from django import forms
from .models import SparePart, StockTransaction, Supplier, PartCategory, MachineType


class SparePartForm(forms.ModelForm):
    compatible_machines = forms.ModelMultipleChoiceField(
        queryset=MachineType.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = SparePart
        fields = [
            'part_number', 'name', 'description', 'category', 'compatible_machines',
            'supplier', 'quantity_in_stock', 'minimum_stock_level', 'unit',
            'condition', 'unit_cost', 'storage_location', 'is_active'
        ]
        widgets = {
            'part_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. ATM-RLR-001'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Part name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'quantity_in_stock': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'minimum_stock_level': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'storage_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Shelf A3'}),
        }


class StockTransactionForm(forms.ModelForm):
    class Meta:
        model = StockTransaction
        fields = [
            'transaction_type', 'quantity', 'machine_serial', 'machine_type',
            'recipient_user', 'recipient_name', 'reference_number', 'ticket_number', 'notes',
        ]
        widgets = {
            'transaction_type': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'machine_serial': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Machine serial number'}),
            'machine_type': forms.Select(attrs={'class': 'form-select'}),
            'recipient_user': forms.Select(attrs={'class': 'form-select'}),
            'recipient_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Recipient name (if not a system user)'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Job card / PO number'}),
            'ticket_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Support / job ticket number'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['recipient_user'].required = False
        self.fields['recipient_name'].required = False
        self.fields['ticket_number'].required = False
        self.fields['recipient_user'].empty_label = 'Select a system user (optional)'


class StockTransactionEditForm(forms.ModelForm):
    """
    Used by the 'Edit Transaction' modal on the part detail / dashboard / reports pages.
    Intentionally limited to non-quantity-affecting fields so existing stock
    calculations, alerts, and business logic are never altered by an edit.
    """
    class Meta:
        model = StockTransaction
        fields = [
            'machine_serial', 'machine_type',
            'recipient_user', 'recipient_name',
            'reference_number', 'ticket_number', 'notes',
        ]
        widgets = {
            'machine_serial': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Machine serial number'}),
            'machine_type': forms.Select(attrs={'class': 'form-select'}),
            'recipient_user': forms.Select(attrs={'class': 'form-select'}),
            'recipient_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Recipient name (if not a system user)'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Job card / PO number'}),
            'ticket_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Support / job ticket number'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['recipient_user'].required = False
        self.fields['recipient_name'].required = False
        self.fields['ticket_number'].required = False
        self.fields['recipient_user'].empty_label = 'Select a system user (optional)'


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'email', 'phone', 'address', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class PartCategoryForm(forms.ModelForm):
    class Meta:
        model = PartCategory
        fields = ['name', 'description', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
        }


class MachineTypeForm(forms.ModelForm):
    class Meta:
        model = MachineType
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class StockFilterForm(forms.Form):
    search = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Search parts...'
    }))
    category = forms.ModelChoiceField(queryset=PartCategory.objects.all(), required=False,
                                       widget=forms.Select(attrs={'class': 'form-select'}),
                                       empty_label='All Categories')
    machine_type = forms.ModelChoiceField(queryset=MachineType.objects.all(), required=False,
                                           widget=forms.Select(attrs={'class': 'form-select'}),
                                           empty_label='All Machines')
    stock_status = forms.ChoiceField(
        choices=[('', 'All'), ('low', 'Low Stock'), ('out', 'Out of Stock'), ('ok', 'In Stock')],
        required=False, widget=forms.Select(attrs={'class': 'form-select'})
    )
