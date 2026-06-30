from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class MachineType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class PartCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#123692')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Part Categories'


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class SparePart(models.Model):
    CONDITION_CHOICES = [
        ('new', 'New'), ('used', 'Used'),
        ('refurbished', 'Refurbished'), ('damaged', 'Damaged'),
    ]
    UNIT_CHOICES = [
        ('piece', 'Piece'), ('set', 'Set'), ('pair', 'Pair'),
        ('box', 'Box'), ('roll', 'Roll'), ('meter', 'Meter'),
    ]

    part_number = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(PartCategory, on_delete=models.CASCADE, related_name='parts')
    compatible_machines = models.ManyToManyField(MachineType, related_name='parts', blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    quantity_in_stock = models.PositiveIntegerField(default=0)
    minimum_stock_level = models.PositiveIntegerField(default=5)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='piece')
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='new')
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    storage_location = models.CharField(max_length=100, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='parts_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.part_number} - {self.name}"

    @property
    def is_low_stock(self):
        return 0 < self.quantity_in_stock <= self.minimum_stock_level

    @property
    def is_out_of_stock(self):
        return self.quantity_in_stock == 0

    @property
    def total_value(self):
        return self.quantity_in_stock * self.unit_cost

    class Meta:
        ordering = ['name']


class StockTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('receipt', 'Stock Receipt'), ('issue', 'Stock Issue'),
        ('return', 'Return'), ('adjustment', 'Adjustment'),
        ('damaged', 'Damaged/Write-off'), ('transfer', 'Transfer'),
    ]

    part = models.ForeignKey(SparePart, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    quantity_before = models.PositiveIntegerField()
    quantity_after = models.PositiveIntegerField()
    machine_serial = models.CharField(max_length=100, blank=True)
    machine_type = models.ForeignKey(MachineType, on_delete=models.SET_NULL, null=True, blank=True)
    reference_number = models.CharField(max_length=100, blank=True)
    ticket_number = models.CharField(
        max_length=100, blank=True,
        help_text="Optional support/job ticket number associated with this transaction (entered manually)."
    )
    notes = models.TextField(blank=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    performed_at = models.DateTimeField(default=timezone.now)

    # ── Recipient tracking (additive — does not affect existing logic) ──
    recipient_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='parts_received',
        help_text="Select the recipient from existing system users, if applicable."
    )
    recipient_name = models.CharField(
        max_length=150, blank=True,
        help_text="Name of the person the part was issued/given to (free text, used if recipient is not a system user)."
    )

    def __str__(self):
        return f"{self.part.part_number} | {self.get_transaction_type_display()} | {self.quantity}"

    @property
    def recipient_display(self):
        """Best-available label for who received this part, for display in lists/reports."""
        if self.recipient_user_id:
            return self.recipient_user.get_full_name() or self.recipient_user.username
        return self.recipient_name or '—'

    class Meta:
        ordering = ['-performed_at']


class StockAlert(models.Model):
    ALERT_TYPES = [('low_stock', 'Low Stock'), ('out_of_stock', 'Out of Stock')]
    STATUS_CHOICES = [('active', 'Active'), ('acknowledged', 'Acknowledged'), ('resolved', 'Resolved')]

    part = models.ForeignKey(SparePart, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    quantity_at_alert = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.part.name} - {self.get_alert_type_display()}"

    class Meta:
        ordering = ['-created_at']
