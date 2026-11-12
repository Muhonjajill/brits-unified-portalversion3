from datetime import date, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


# Absence types that may be submitted at short notice. The paper form says:
# "You must submit requests for absences, other than sick leave, two days
# prior to the first day you will be absent." Add e.g. 'bereavement' here if
# you want to exempt more types.
NOTICE_EXEMPT_TYPES = ('sick',)
NOTICE_DAYS = 2


class LeaveApplication(models.Model):
    # ── Status ────────────────────────────────────────────────────────────────
    STATUS_DRAFT = 'draft'
    STATUS_SUBMITTED = 'submitted'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_WITHDRAWN = 'withdrawn'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_WITHDRAWN, 'Withdrawn'),
    ]

    # ── Type of absence (as on the BRTS paper form) ───────────────────────────
    TYPE_SICK = 'sick'
    TYPE_VACATION = 'vacation'
    TYPE_BEREAVEMENT = 'bereavement'
    TYPE_UNPAID = 'unpaid'
    TYPE_JURY_DUTY = 'jury_duty'
    TYPE_PARENTAL = 'parental'
    TYPE_OTHER = 'other'

    TYPE_CHOICES = [
        (TYPE_SICK, 'Sick'),
        (TYPE_VACATION, 'Vacation'),
        (TYPE_BEREAVEMENT, 'Bereavement'),
        (TYPE_UNPAID, 'Time Off Without Pay'),
        (TYPE_JURY_DUTY, 'Jury Duty'),
        (TYPE_PARENTAL, 'Maternity/Paternity'),
        (TYPE_OTHER, 'Other'),
    ]

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='leave_applications',
    )
    employee_number = models.CharField(max_length=50, blank=True)

    leave_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    other_type_detail = models.CharField(
        max_length=120, blank=True,
        help_text="Describe the absence when the type is 'Other'",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()

    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='leaves_to_manage',
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    manager_comment = models.TextField(blank=True)
    manager_actioned_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.employee.get_full_name()} — {self.get_leave_type_display()} "
            f"{self.start_date:%d %b %Y}–{self.end_date:%d %b %Y} ({self.get_status_display()})"
        )

    # ── Display helpers ───────────────────────────────────────────────────────
    @property
    def type_label(self):
        if self.leave_type == self.TYPE_OTHER and self.other_type_detail:
            return f"Other — {self.other_type_detail}"
        return self.get_leave_type_display()

    @property
    def working_days(self):
        """Weekdays (Mon–Fri) from start to end inclusive. Public holidays are not excluded."""
        return count_working_days(self.start_date, self.end_date)

    @property
    def calendar_days(self):
        if not self.start_date or not self.end_date:
            return 0
        return (self.end_date - self.start_date).days + 1

    @property
    def status_color(self):
        return {
            self.STATUS_DRAFT: 'secondary',
            self.STATUS_SUBMITTED: 'primary',
            self.STATUS_APPROVED: 'success',
            self.STATUS_REJECTED: 'danger',
            self.STATUS_WITHDRAWN: 'warning',
        }.get(self.status, 'secondary')

    @property
    def is_editable(self):
        return self.status in (self.STATUS_DRAFT, self.STATUS_REJECTED)

    @property
    def needs_notice(self):
        return self.leave_type not in NOTICE_EXEMPT_TYPES

    # ── Workflow ──────────────────────────────────────────────────────────────
    def can_approve(self, user):
        return self.status == self.STATUS_SUBMITTED and self.manager_id == user.pk

    def submit(self):
        self.status = self.STATUS_SUBMITTED
        self.submitted_at = timezone.now()
        # Clear an earlier decision when a rejected application is resubmitted
        self.manager_comment = ''
        self.manager_actioned_at = None
        self.save()

    def approve(self, user, comment=''):
        if self.can_approve(user):
            self.status = self.STATUS_APPROVED
            self.manager_comment = comment
            self.manager_actioned_at = timezone.now()
            self.save()

    def reject(self, user, comment=''):
        if self.can_approve(user):
            self.status = self.STATUS_REJECTED
            self.manager_comment = comment
            self.manager_actioned_at = timezone.now()
            self.save()

    def withdraw(self):
        self.status = self.STATUS_WITHDRAWN
        self.withdrawn_at = timezone.now()
        self.save()


def count_working_days(start, end):
    if not start or not end or end < start:
        return 0
    days, d = 0, start
    while d <= end:
        if d.weekday() < 5:
            days += 1
        d += timedelta(days=1)
    return days


def earliest_start_for(leave_type, today=None):
    """First start date allowed by the notice rule for this absence type."""
    today = today or date.today()
    if leave_type in NOTICE_EXEMPT_TYPES:
        return None
    return today + timedelta(days=NOTICE_DAYS)
