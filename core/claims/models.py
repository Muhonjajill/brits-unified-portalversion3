from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


class ClaimForm(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_SUBMITTED = 'submitted'
    STATUS_MANAGER_APPROVED = 'manager_approved'
    STATUS_HR_APPROVED = 'hr_approved'
    STATUS_FINANCE_APPROVED = 'finance_approved'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_MANAGER_APPROVED, 'Manager Approved'),
        (STATUS_HR_APPROVED, 'HR Approved'),
        (STATUS_FINANCE_APPROVED, 'Finance Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='claim_forms'
    )
    title = models.CharField(max_length=200, blank=True)
    month = models.DateField(help_text="Month this claim covers (use first day of month)")
    advance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    # Approval chain
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='claims_to_manage'
    )
    hr_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='claims_to_hr_review'
    )
    finance_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='claims_to_finance_review'
    )

    manager_comment = models.TextField(blank=True)
    hr_comment = models.TextField(blank=True)
    finance_comment = models.TextField(blank=True)

    manager_actioned_at = models.DateTimeField(null=True, blank=True)
    hr_actioned_at = models.DateTimeField(null=True, blank=True)
    finance_actioned_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        app_label = 'core'

    def __str__(self):
        return f"{self.employee.get_full_name()} — {self.month.strftime('%B %Y')} ({self.get_status_display()})"

    @property
    def subtotal(self):
        return sum(entry.total for entry in self.entries.all())

    @property
    def total_minus_advance(self):
        return self.subtotal - self.advance

    @property
    def status_color(self):
        return {
            self.STATUS_DRAFT: 'secondary',
            self.STATUS_SUBMITTED: 'primary',
            self.STATUS_MANAGER_APPROVED: 'info',
            self.STATUS_HR_APPROVED: 'warning',
            self.STATUS_FINANCE_APPROVED: 'success',
            self.STATUS_REJECTED: 'danger',
        }.get(self.status, 'secondary')

    @property
    def next_approver_role(self):
        if self.status == self.STATUS_SUBMITTED:
            return 'Manager'
        if self.status == self.STATUS_MANAGER_APPROVED:
            return 'HR'
        if self.status == self.STATUS_HR_APPROVED:
            return 'Finance'
        return None

    def can_approve(self, user):
        if self.status == self.STATUS_SUBMITTED and self.manager == user:
            return True
        if self.status == self.STATUS_MANAGER_APPROVED and self.hr_reviewer == user:
            return True
        if self.status == self.STATUS_HR_APPROVED and self.finance_reviewer == user:
            return True
        return False

    def approve(self, user, comment=''):
        now = timezone.now()
        if self.status == self.STATUS_SUBMITTED and self.manager == user:
            self.status = self.STATUS_MANAGER_APPROVED
            self.manager_comment = comment
            self.manager_actioned_at = now
        elif self.status == self.STATUS_MANAGER_APPROVED and self.hr_reviewer == user:
            self.status = self.STATUS_HR_APPROVED
            self.hr_comment = comment
            self.hr_actioned_at = now
        elif self.status == self.STATUS_HR_APPROVED and self.finance_reviewer == user:
            self.status = self.STATUS_FINANCE_APPROVED
            self.finance_comment = comment
            self.finance_actioned_at = now
        self.save()

    def reject(self, user, comment=''):
        now = timezone.now()
        self.status = self.STATUS_REJECTED
        if self.manager == user:
            self.manager_comment = comment
            self.manager_actioned_at = now
        elif self.hr_reviewer == user:
            self.hr_comment = comment
            self.hr_actioned_at = now
        elif self.finance_reviewer == user:
            self.finance_comment = comment
            self.finance_actioned_at = now
        self.save()


class ClaimEntry(models.Model):
    claim = models.ForeignKey(ClaimForm, on_delete=models.CASCADE, related_name='entries')
    date = models.DateField()
    site = models.CharField(max_length=200)
    job_card_id = models.CharField(max_length=100, blank=True)
    transport_to = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    transport_from = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    breakfast = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    lunch = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    dinner = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    bed = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['date', 'order']
        app_label = 'core'

    def __str__(self):
        return f"{self.date} — {self.site}"

    @property
    def total(self):
        return (
            self.transport_to + self.transport_from +
            self.breakfast + self.lunch +
            self.dinner + self.bed
        )
