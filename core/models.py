from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from core.priority_rules import determine_priority


class EmailOTP(models.Model):
        user = models.OneToOneField(User, on_delete=models.CASCADE)
        otp = models.CharField(max_length=6)
        created_at = models.DateTimeField(auto_now_add=True)

        def is_expired(self):
            now = timezone.now()
            return now >  self.created_at + timedelta(minutes=50) 
        
        def __str__(self):
            return f"{self.user.username} - {self.otp}"
        
# File Management Models
class FileCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=255, default='default_icon')

    def __str__(self):
        return self.name
    
ACCESS_LEVEL_CHOICES = [
    ('confidential', 'Confidential'),
    ('restricted', 'Restricted'),
    ('public', 'Public'),
]

class File(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='uploads/files/')
    category = models.ForeignKey(FileCategory, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    authorized_users = models.ManyToManyField(User, blank=True, related_name='authorized_files')
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVEL_CHOICES, default='public')
    passcode = models.CharField(max_length=50, blank=True, null=True)  
    allow_preview = models.BooleanField(default=True)
    allow_download = models.BooleanField(default=True)

    def can_user_access(self, user, passcode=None):
        if self.access_level == 'public':
            return True
        if self.access_level == 'restricted':
            if user in self.authorized_users.all() or user.has_perm('core.view_file'):
                return True
            # Check passcode for restricted files
            if passcode and passcode == self.passcode:
                return True
            return False
        if self.access_level == 'confidential':
            return self.uploaded_by == user or user.is_superuser
        return False


class FileAccessLog(models.Model):
    file = models.ForeignKey(File, on_delete=models.CASCADE)
    accessed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    access_time = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=50, choices=[('preview', 'Preview'), ('download', 'Download')], null=True)

    def __str__(self):
        return f"{self.accessed_by} {self.action}d {self.file.title} at {self.access_time}"

def user_directory_path(instance, filename):
    return f'user_{instance.user.id}/{filename}'

"""
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to=user_directory_path, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)  
    id_number = models.CharField(max_length=20, blank=True, null=True) 
    role = models.CharField(max_length=100, blank=True, default='Guest') 
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, null=True, blank=True)
    terminal = models.ForeignKey('Terminal', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.user.username
"""

class Profile(models.Model):
    ROLE_CHOICES = [
        ('Admin', 'Admin'),
        ('Director', 'Director'),
        ('Manager', 'Manager'),
        ('Staff', 'Staff'),
        ('Customer', 'Customer'),
        ('Overseer', 'Overseer'),
        ('Custodian', 'Custodian'),
        ('Guest', 'Guest'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to=user_directory_path, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)  
    id_number = models.CharField(max_length=20, blank=True, null=True) 
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='Guest')
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, null=True, blank=True)
    terminal = models.ForeignKey('Terminal', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.user.username


# Help desk models
class Unit(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Terminal(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, null=True)
    custodian = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='custodian_terminals')
    branch_name = models.CharField(max_length=100, default='Main Branch')
    cdm_name = models.CharField(max_length=100, default='CDM-Default')
    serial_number = models.CharField(max_length=100, unique=False, default='SN0000')
    region = models.ForeignKey('Region', on_delete=models.CASCADE, null=True)
    model = models.CharField(max_length=100, default='ModelX')
    zone = models.ForeignKey('Zone', on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True) 

    def __str__(self):
        return f"{self.customer.name if self.customer else 'No Customer'} - {self.branch_name}"
    
    def is_overseer(self, user):
        return self.customer.overseer == user

    def is_custodian(self, user):
        return self.customer.custodian == user


class SystemUser(models.Model):
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField()
    role = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=15, blank=True, null=True) 

    def __str__(self):
        return self.username

class Zone(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Customer(models.Model):
    name = models.CharField(max_length=100)
    overseer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='overseeing_branches')
    custodian = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='custodians_of_customers')

    def __str__(self):
        return self.name

class Region(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

# ---- ISSUE mappimg ---- #
ISSUE_MAPPING = {
    "Hardware Related": [
        "Note rejects",
        "Hardware Error",
        "Broken part",
        "Note jams pathway",
        "Note jams Escrow",
    ],
    "Software Related": [
        "Out of Service",
        "Account validation failing",
        "Application offline",
        "Application Unresponsive",
        "Application Update",
        "Front screen unavailable",
        "Failed Transactions on terminal",
        "Server Update",
        "E journal not uploading",
        "Template Update",
        "Firmware update",
    ],
    "Cash Reconciliation": [
        "Excess cash",
        "Cash shortage",
    ],
    "Power and Network": [
        "System off",
        "System Offline",
        "Faulty UPS/No clean Power",
    ],
    "De-/Installation /Maintenance": [
        "Relocation",
        "Configuration",
        "Quarterly PM",
        "Re-imaging of the terminal",
    ],
    "Safe": [
        "Lock/Key jam",
        "Door jam",
    ],
    "SLA Related": [
        "General Complaint",
    ],
}

CATEGORY_CHOICES = [(cat, cat) for cat in ISSUE_MAPPING.keys()]


# Problem category now stores a specific issue (choice from ISSUE_CHOICES)
class ProblemCategory(models.Model):
    brts_unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True,
      blank=True)
    name = models.CharField(max_length=100, choices=CATEGORY_CHOICES)

    def __str__(self):
        return self.name
"""
class ProblemCategory(models.Model):
    brts_unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.brts_unit.name})"
"""

class VersionControl(models.Model):

    MANUFACTURER_CHOICES = [
        ('GRG Banking', 'GRG Banking'),
        ('Hitachi', 'Hitachi'),
    ]
    
    manufacturer = models.CharField(
        max_length=100,
        choices=MANUFACTURER_CHOICES,
        default='GRG Banking'
    )
    terminal = models.ForeignKey(Terminal, on_delete=models.CASCADE)
    #manufacturer = models.CharField(max_length=100)
    template = models.CharField(max_length=100)
    firmware = models.CharField(max_length=100)
    xfs = models.CharField(max_length=100,  blank=True, null=True)  
    ejournal = models.CharField(max_length=100,  blank=True, null=True) 
    #responsible = models.CharField(max_length=100,  default='N/A')  
    app_version = models.CharField(max_length=100, blank=True, null=True)
    # New fields
    neo_atm = models.CharField(max_length=100, blank=True, null=True)
    brits = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    

    def __str__(self):
        return f"{self.terminal} - {self.firmware}"
    
class VersionComment(models.Model):
    version = models.ForeignKey(VersionControl, related_name='comments', on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:50]  #  
class Report(models.Model):
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50)
    generated_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='reports/')

    def __str__(self):
        return self.name

    def download_url(self):
        return self.file.url

class UserNotification(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    ticket     = models.ForeignKey("Ticket", on_delete=models.CASCADE, related_name="notifications")
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "ticket"], name="unique_user_ticket_notification")
        ]
    def __str__(self):
        return f"Notification for {self.user.username} - Ticket #{self.ticket.id}"

class Ticket(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    ESCALATION_LEVELS = [
        ('Tier 1', 'Tier 1'),
        ('Tier 2', 'Tier 2'),
        ('Tier 3', 'Tier 3'),
        ('Tier 4', 'Tier 4'),
    ]

    title = models.CharField(max_length=255, default="Unknown Issue")
    brts_unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True)
    problem_category = models.ForeignKey(ProblemCategory, on_delete=models.SET_NULL, null=True)
    terminal = models.ForeignKey(Terminal, on_delete=models.CASCADE, null=True, blank=True)
    zone = models.ForeignKey('Zone', on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField()

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=False, blank=False)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, null=False, blank=False)

    created_by = models.ForeignKey(User, related_name='created_tickets', on_delete=models.SET_NULL, null=True)
    assigned_to = models.ForeignKey(User, related_name='assigned_tickets', on_delete=models.SET_NULL, null=True, blank=True)
    responsible = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    resolution = models.TextField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, related_name='resolved_tickets', null=True, blank=True, on_delete=models.SET_NULL)
    resolved_at = models.DateTimeField(null=True, blank=True)
    comment_summary = models.TextField(blank=True, null=True)
    due_date = models.DateTimeField(null=True, blank=True)

    is_escalated = models.BooleanField(default=False)
    escalated_at = models.DateTimeField(null=True, blank=True)
    escalated_by = models.ForeignKey(
        User, null=True, blank=True, related_name='escalated_tickets', on_delete=models.SET_NULL
    )
    escalation_reason = models.TextField(null=True, blank=True)
    current_escalation_level = models.CharField(max_length=20, choices=ESCALATION_LEVELS, blank=True, null=True)

    escalation_action = models.TextField(null=True, blank=True)
    escalation_type = models.CharField(max_length=100, null=True, blank=True)

    #created_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name='updated_tickets',
        on_delete=models.SET_NULL
    )
    
    class Meta:
        permissions = [
            ('can_view_ticket', 'Can view ticket'),
            ('can_resolve_ticket', 'Can resolve ticket'),
        ]

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if self.terminal and not self.zone:
            self.zone = self.terminal.zone

        if self.problem_category and self.priority:
            from core.utilss.escalation import get_escalation_guidance
            guidance = get_escalation_guidance(self.problem_category.name, self.priority)
            self.escalation_type = guidance['escalation_type']
            self.escalation_action = guidance['escalation_action']

            if not self.current_escalation_level:
                self.current_escalation_level = guidance['escalation_tier']

        if not self.priority:
            self.priority = determine_priority(
                self.problem_category.name if self.problem_category else "",
                self.title,
                self.description
            )

        super().save(*args, **kwargs)

class EscalationHistory(models.Model):
        
        ESCALATION_LEVELS = [
            ('Tier 1', 'Tier 1'),
            ('Tier 2', 'Tier 2'),
            ('Tier 3', 'Tier 3'),
            ('Tier 4', 'Tier 4'),
        ]

        ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="escalation_history")
        escalated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
        from_level = models.CharField(max_length=20, choices=ESCALATION_LEVELS , blank=True, null=True)
        to_level = models.CharField(max_length=20, choices=ESCALATION_LEVELS )
        note = models.TextField(blank=True)
        timestamp = models.DateTimeField(auto_now_add=True)
        
class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ticket.id}" - {self.created_by} 

class ActivityLog(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)  
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=1000)


    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['ticket', 'timestamp']),
        ]


    def _str_(self):
        return f'{self.ticket.title if self.ticket else "Unknown Ticket"} - {self.action}' 