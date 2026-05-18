from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


class ClaimForm(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_SUBMITTED = 'submitted'
    STATUS_MANAGER_APPROVED = 'manager_approved'
    STATUS_FINANCE_APPROVED = 'finance_approved'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_MANAGER_APPROVED, 'Manager Approved'),
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

    # ── Advance tracking ────────────────────────────────────────────────────────
    advance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    carry_forward = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text="Balance carried forward from the previous approved claim"
    )
    previous_claim = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='next_claims',
        help_text="The prior approved claim whose balance was carried into this one"
    )

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='claims_to_manage'
    )
    finance_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='claims_to_finance_review'
    )

    # ── amount_paid is now the SUM of all PaymentRecord entries ─────────────────
    # Kept as a cached/denormalised field for fast querying & carry-forward maths.
    # Always refresh via refresh_amount_paid() after adding a PaymentRecord.
    amount_paid = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text="Total amount actually disbursed by Finance (sum of payment records)"
    )
    finance_paid_at = models.DateTimeField(null=True, blank=True)
    finance_paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='claims_paid_out'
    )

    manager_comment = models.TextField(blank=True)
    finance_comment = models.TextField(blank=True)

    manager_actioned_at = models.DateTimeField(null=True, blank=True)
    finance_actioned_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee.get_full_name()} — {self.month.strftime('%B %Y')} ({self.get_status_display()})"

    def get_auto_title(self):
        first = self.employee.first_name or self.employee.username
        suffix = "'s" if not first.endswith('s') else "'"
        return f"{first}{suffix} Claim Form"

    @property
    def display_title(self):
        return self.title or self.get_auto_title()

    @property
    def total_advance(self):
        """Combined advance: carried-forward balance + new advance issued."""
        return self.carry_forward + self.advance

    @property
    def subtotal(self):
        return sum(entry.total for entry in self.entries.all())

    @property
    def total_minus_advance(self):
        return self.subtotal - self.total_advance

    @property
    def balance_due(self):
        """
        Amount still owed after advance/carry-forward and any recorded payments.
        Positive  → employer still owes the employee.
        Negative  → employee was overpaid (excess becomes next claim's carry-forward).
        """
        return self.subtotal - self.total_advance - self.amount_paid

    @property
    def overpayment(self):
        """
        How much Finance has paid above and beyond what was owed.
        Returns 0 if the claim has not been overpaid.
        """
        excess = self.amount_paid - self.total_minus_advance
        return max(excess, Decimal('0.00'))

    @property
    def is_fully_paid(self):
        return (
            self.status == self.STATUS_FINANCE_APPROVED
            and self.amount_paid > Decimal('0.00')
            and self.amount_paid >= self.total_minus_advance
        )

    @property
    def status_color(self):
        return {
            self.STATUS_DRAFT: 'secondary',
            self.STATUS_SUBMITTED: 'primary',
            self.STATUS_MANAGER_APPROVED: 'info',
            self.STATUS_FINANCE_APPROVED: 'success',
            self.STATUS_REJECTED: 'danger',
        }.get(self.status, 'secondary')

    @property
    def next_approver_role(self):
        if self.status == self.STATUS_SUBMITTED:
            return 'Manager'
        if self.status == self.STATUS_MANAGER_APPROVED:
            return 'Finance'
        return None

    def can_approve(self, user):
        if self.status == self.STATUS_SUBMITTED and self.manager == user:
            return True
        if self.status == self.STATUS_MANAGER_APPROVED and self.finance_reviewer == user:
            return True
        return False

    def approve(self, user, comment=''):
        now = timezone.now()
        if self.status == self.STATUS_SUBMITTED and self.manager == user:
            self.status = self.STATUS_MANAGER_APPROVED
            self.manager_comment = comment
            self.manager_actioned_at = now
        elif self.status == self.STATUS_MANAGER_APPROVED and self.finance_reviewer == user:
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
        elif self.finance_reviewer == user:
            self.finance_comment = comment
            self.finance_actioned_at = now
        self.save()

    def refresh_amount_paid(self):
        """
        Recompute the denormalised amount_paid from PaymentRecord rows.
        Call this after every PaymentRecord insert/update/delete.
        """
        from django.db.models import Sum
        total = self.payment_records.aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
        self.amount_paid = total
        # Keep finance_paid_at / finance_paid_by pointing at the most recent record
        last = self.payment_records.order_by('-paid_at').first()
        if last:
            self.finance_paid_at = last.paid_at
            self.finance_paid_by = last.recorded_by
        self.save(update_fields=['amount_paid', 'finance_paid_at', 'finance_paid_by'])

    def get_previous_claim(self):
        """Most recent finance-approved claim for this employee before this month."""
        if not self.employee or not self.month:
            return None
        return (
            ClaimForm.objects.filter(
                employee=self.employee,
                month__lt=self.month,
                status=self.STATUS_FINANCE_APPROVED,
            )
            .order_by('-month')
            .first()
        )

    def get_latest_approved_claim(self):
        """
        Most recent finance-approved claim for this employee, regardless of month.
        Used for same-month carry-forward scenarios.
        """
        if not self.employee:
            return None
        return (
            ClaimForm.objects.filter(
                employee=self.employee,
                status=self.STATUS_FINANCE_APPROVED,
            )
            .exclude(pk=self.pk)
            .order_by('-month', '-finance_actioned_at')
            .first()
        )

    def compute_carry_forward(self):
        """
        Calculate the balance that should be carried forward from the last
        finance-approved claim — including same-month claims.

        balance_due = subtotal - total_advance - amount_paid
        Positive  → employer still owes employee (carried forward as advance).
        Negative  → employee was overpaid (deducted from next claim advance).

        Returns (prev_claim, carry_forward_amount).
        """
        # Use latest approved claim (not restricted to earlier months) so that
        # overpayments in the same month are also captured.
        prev = self.get_latest_approved_claim()
        if prev is None:
            return None, Decimal('0.00')
        carry = prev.balance_due  # can be negative (overpayment)
        return prev, carry

    def get_claim_history(self):
        """All prior claims for this employee, newest first."""
        return (
            ClaimForm.objects.filter(employee=self.employee)
            .exclude(pk=self.pk)
            .order_by('-month')
        )


class PaymentRecord(models.Model):
    """
    Individual disbursement made by Finance against a ClaimForm.
    Replaces the single amount_paid field with a full audit trail.
    Multiple records can exist per claim (e.g. partial payments).
    """
    claim = models.ForeignKey(
        ClaimForm,
        on_delete=models.CASCADE,
        related_name='payment_records'
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Amount disbursed in this payment"
    )
    note = models.CharField(
        max_length=255, blank=True,
        help_text="Optional note (e.g. 'Partial payment — balance pending')"
    )
    paid_at = models.DateTimeField(default=timezone.now)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='payment_records_created'
    )

    class Meta:
        ordering = ['paid_at']

    def __str__(self):
        return (
            f"KES {self.amount} → {self.claim.employee.get_full_name()} "
            f"({self.claim.month.strftime('%b %Y')}) on {self.paid_at:%d %b %Y}"
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Keep the denormalised total in sync automatically
        self.claim.refresh_amount_paid()

    def delete(self, *args, **kwargs):
        claim = self.claim
        super().delete(*args, **kwargs)
        claim.refresh_amount_paid()


class ClaimEntry(models.Model):
    claim = models.ForeignKey(ClaimForm, on_delete=models.CASCADE, related_name='entries')
    date = models.DateField()
    site = models.CharField(max_length=200)
    ticket_number = models.CharField(max_length=100, blank=True, help_text="Ticket / job reference number")
    ticket_url = models.URLField(max_length=500, blank=True, help_text="Direct URL to the ticket (optional)")
    transport_to = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    transport_from = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    breakfast = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    lunch = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    dinner = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    bed = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['date', 'order']

    def __str__(self):
        return f"{self.date} — {self.site}"

    @property
    def total(self):
        return (
            self.transport_to + self.transport_from +
            self.breakfast + self.lunch +
            self.dinner + self.bed
        )