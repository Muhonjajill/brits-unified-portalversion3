# forms.py
from django import forms
from .models import File, ProblemCategory, Ticket,TicketComment, Customer, Region, ISSUE_MAPPING, CATEGORY_CHOICES
from django.contrib.auth.models import User
from .models import Profile, Terminal, VersionControl
from core.priority_rules import determine_priority

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

class OTPForm(forms.Form):
    otp = forms.CharField(max_length=6)

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class CustomUserCreationForm(forms.ModelForm):
    password = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)
    phone = forms.CharField(max_length=15, required=True, widget=forms.TextInput(attrs={'placeholder': 'Phone Number'}))
    id_number = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={'placeholder': 'ID Number'}))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'phone', 'id_number']

    def clean_password2(self):
        password = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')

        if password and password2 and password != password2:
            raise forms.ValidationError("Passwords don’t match.")
        return password2

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError("A user with that username already exists.")
        return username

    """
    def save(self, commit=True):
        # Save the user without committing to the database
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        
        # Commit and save the user
        if commit:
            user.save()

        # Get or create the profile
        profile, created = Profile.objects.get_or_create(user=user)
        
        # If the profile is created, set phone_number and id_number
        if created:
            print(f"Profile Created: {profile}")
            profile.phone_number = self.cleaned_data['phone']
            profile.id_number = self.cleaned_data['id_number']
            profile.save()
        else:
            # If profile exists, just update phone and id number
            print(f"Updating Profile: {profile}")
            profile.phone_number = self.cleaned_data['phone']
            profile.id_number = self.cleaned_data['id_number']
            profile.save()

        return user
        """
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()

        profile, created = Profile.objects.get_or_create(user=user)

        if created:
            profile.phone_number = self.cleaned_data['phone']
            profile.id_number = self.cleaned_data['id_number']

            # ✅ Explicitly set role here
            profile.role = 'Guest'   # Or whatever default you want
            profile.save()
        else:
            profile.phone_number = self.cleaned_data['phone']
            profile.id_number = self.cleaned_data['id_number']
            profile.save()

        return user





    
class FileUploadForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ['title', 'description', 'category', 'access_level', 'file', 'passcode', 'allow_preview', 'allow_download']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter file title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter a brief description', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'access_level': forms.Select(attrs={'class': 'form-control'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'passcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Set a passcode for restricted access'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.access_level != 'restricted':
            self.fields['passcode'].required = False  
        else:
            self.fields['passcode'].required = True



class FilePasscodeForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ['passcode']
        widgets = {
            'passcode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter new passcode'
            })
        }

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email']

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar', 'phone_number', 'id_number', 'role']  # Include role but make it read-only

    phone_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    id_number = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        user = kwargs.get('instance').user
        super().__init__(*args, **kwargs)

        # Handle visibility of role, customer, and terminal based on user role
        if user.profile.role == 'Customer':
            # Exclude role, customer, terminal for Customer role
            self.fields.pop('role', None)
            self.fields.pop('customer', None)
            self.fields.pop('terminal', None)
        elif user.profile.role == 'Overseer':
            # For Overseer, make customer read-only but show terminal
            self.fields['customer'].widget.attrs['disabled'] = True
        elif user.profile.role == 'Custodian':
            # For Custodian, make terminal read-only but show customer
            self.fields['terminal'].widget.attrs['disabled'] = True
        
        # Make role field read-only (not editable)
        if 'role' in self.fields:
            self.fields['role'].disabled = True




class TicketForm(forms.ModelForm):
    problem_category = forms.ModelChoiceField(
        queryset=ProblemCategory.objects.all(),
        empty_label="Select Category",
        required=False,
        widget=forms.Select(attrs={"class": "form-control"})
    )
    title = forms.ChoiceField(
        choices=[("", "Select Issue")],
        required=False,
        widget=forms.Select(attrs={"class": "form-control"})
    )
    custom_created_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control'
        })
    )
    class Meta:
        model = Ticket
        fields = [
            "brts_unit",
            "problem_category",
            "title",
            "terminal",
            "customer",
            "region",
            "description",
            "status",
        ] 
        exclude = ['created_by', 'assigned_to', 'created_at', 'updated_at']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'brts_unit': forms.Select(attrs={'class': 'form-control'}),
            'problem_category': forms.Select(attrs={'class': 'form-control'}),
            'terminal': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    # Override to make them required and visible
    customer = forms.ModelChoiceField(queryset=Customer.objects.all(), required=True)
    region = forms.ModelChoiceField(queryset=Region.objects.all(), required=True)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)  
        terminal_id = kwargs.pop('terminal_id', None)
        super().__init__(*args, **kwargs)

        # Default queryset (all terminals)
        self.fields['terminal'].queryset = Terminal.objects.all()
        self.fields['terminal'].label_from_instance = lambda obj: (
            f"{obj.cdm_name} (Inactive)" if not obj.is_active else obj.cdm_name
        )

        # Autofill if instance has a terminal
        if self.instance and getattr(self.instance, 'terminal', None):
            terminal = self.instance.terminal
            self.fields['customer'].initial = terminal.customer
            self.fields['region'].initial = terminal.region
        elif terminal_id:
            try:
                terminal = Terminal.objects.get(id=terminal_id)
                self.fields['customer'].initial = terminal.customer
                self.fields['region'].initial = terminal.region
            except Terminal.DoesNotExist:
                pass

        # Populate issue choices based on selected category
        selected = self.data.get("problem_category") or self.initial.get("problem_category")
        if selected:
            try:
                cat = ProblemCategory.objects.get(pk=selected)
                issues = ISSUE_MAPPING.get(cat.name, [])
                self.fields["title"].choices = [("", "Select Issue")] + [(i, i) for i in issues]
                self.fields["title"].widget.attrs.pop("disabled", None)
            except ProblemCategory.DoesNotExist:
                self.fields["title"].widget.attrs["disabled"] = True
        else:
            self.fields["title"].widget.attrs["disabled"] = True

        # Role-based restrictions
        if self.user:
            profile = getattr(self.user, "profile", None)

            # If user is custodian → only his terminal, customer, and region
            if profile and getattr(profile, "terminal", None):
                assigned_terminal = profile.terminal
                assigned_customer = assigned_terminal.customer
                assigned_region = assigned_terminal.region

                self.fields['terminal'].queryset = Terminal.objects.filter(id=assigned_terminal.id)
                self.fields['customer'].queryset = Customer.objects.filter(id=assigned_customer.id)
                self.fields['region'].queryset = Region.objects.filter(id=assigned_region.id)

                # Lock customer and region fields (but don't disable them)
                self.fields['customer'].initial = assigned_customer
                self.fields['region'].initial = assigned_region
                self.fields['terminal'].disabled = True
                self.fields['customer'].disabled = True
                self.fields['region'].disabled = True

            # If user is overseer → all terminals of his customer, customer locked, region limited
            elif Customer.objects.filter(overseer=self.user).exists():
                assigned_customer = Customer.objects.filter(overseer=self.user).first()

                self.fields['customer'].queryset = Customer.objects.filter(id=assigned_customer.id)
                self.fields['terminal'].queryset = Terminal.objects.filter(customer=assigned_customer)
                self.fields['region'].queryset = Region.objects.filter(
                    id__in=self.fields['terminal'].queryset.values_list("region_id", flat=True)
                )

                # Lock customer, region/terminal remain selectable
                self.fields['customer'].initial = assigned_customer
                self.fields['customer'].disabled = True


    def save(self, commit=True):
        # Always compute priority here (never included on the form)
        ticket = super().save(commit=False)
        cat = self.cleaned_data.get("problem_category")
        issue = self.cleaned_data.get("title") or ""
        desc = self.cleaned_data.get("description") or ""
        ticket.priority = determine_priority(
            cat.name if cat else "",
            issue,
            desc
        )

        if hasattr(self, 'user') and hasattr(self.user, 'profile'):
            profile = self.user.profile
            if profile.terminal:
                ticket.terminal = profile.terminal
                ticket.customer = profile.terminal.customer
                ticket.region = profile.terminal.region
                
        if commit:
            ticket.save()
        return ticket


class ProblemCategoryForm(forms.ModelForm):
    class Meta:
        model = ProblemCategory
        fields = ['brts_unit', 'name']
        widgets = {
            'brts_unit': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter category name'}),
        }

class TerminalForm(forms.ModelForm):
    class Meta:
        model = Terminal
        fields = ['customer', 'branch_name', 'cdm_name', 'serial_number', 'region', 'model', 'zone']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'branch_name': forms.TextInput(attrs={'class': 'form-control', 'value': 'Main Branch'}),
            'cdm_name': forms.TextInput(attrs={'class': 'form-control'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'region': forms.Select(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'zone': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.branch_name:
            self.fields['branch_name'].required = False  

    
class TerminalUploadForm(forms.Form):
    file = forms.FileField(
        label='Upload CSV or Excel File',
        widget=forms.FileInput(attrs={'accept': '.csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'})
    )

class VersionControlForm(forms.ModelForm):
    class Meta:
        model = VersionControl
        fields = [
            'terminal', 'manufacturer', 'template', 'firmware',
            'xfs', 'ejournal',
            'brits', 'app_version', 'neo_atm'
        ]
        widgets = {
            'terminal': forms.Select(attrs={'class': 'form-control'}),
            'manufacturer': forms.Select(attrs={'class': 'form-select'}),
            'template': forms.TextInput(attrs={'class': 'form-control'}),
            'firmware': forms.TextInput(attrs={'class': 'form-control'}),
            'xfs': forms.TextInput(attrs={'class': 'form-control'}),
            'ejournal': forms.TextInput(attrs={'class': 'form-control'}),
            #'responsible': forms.TextInput(attrs={'class': 'form-control'}),
            'brits': forms.TextInput(attrs={'class': 'form-control'}),
            'app_version': forms.TextInput(attrs={'class': 'form-control'}),
            'neo_atm': forms.TextInput(attrs={'class': 'form-control'}),
        }

        
class TicketCommentForm(forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Add a comment...', 'class': 'form-control'})
        }

class TicketEditForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['status', 'priority', 'comment_summary', 'problem_category', 'description','resolution']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'comment_summary': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'problem_category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'resolution': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class EscalationNoteForm(forms.Form):
    note = forms.CharField(
        label="Escalation Note",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add a note for the escalation'
        }),
        required=False
    )