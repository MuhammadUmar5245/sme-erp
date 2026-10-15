from django.conf import settings
from django.db import models

from core.fields import EncryptedTextField, mask
from core.models import TimeStampedModel, money_field


class Department(TimeStampedModel):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Employee(TimeStampedModel):
    employee_no = models.CharField(max_length=20, unique=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="employee")
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="employees")
    manager = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="reports")
    job_title = models.CharField(max_length=100)
    hire_date = models.DateField()
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    city = models.CharField(max_length=50, default="Muscat")
    nationality = models.CharField(max_length=50, default="Omani")
    basic_salary = money_field(help_text="Monthly basic salary (OMR)")
    national_id = EncryptedTextField("Civil ID / resident card", blank=True,
                                     help_text="Encrypted at rest")
    bank_iban = EncryptedTextField("Bank IBAN", blank=True, help_text="Encrypted at rest")
    annual_leave_days = models.PositiveSmallIntegerField(default=30, help_text="Annual entitlement (Oman labour law: 30)")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["employee_no"]

    def __str__(self):
        return f"{self.employee_no} - {self.full_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def national_id_masked(self):
        return mask(self.national_id)

    @property
    def bank_iban_masked(self):
        return mask(self.bank_iban)


class LeaveRequest(TimeStampedModel):
    class Type(models.TextChoices):
        ANNUAL = "ANNUAL", "Annual leave"
        SICK = "SICK", "Sick leave"
        EMERGENCY = "EMERGENCY", "Emergency leave"
        UNPAID = "UNPAID", "Unpaid leave"
        MATERNITY = "MATERNITY", "Maternity leave"
        HAJJ = "HAJJ", "Hajj leave"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.CharField(max_length=10, choices=Type.choices, default=Type.ANNUAL)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.DecimalField(max_digits=5, decimal_places=1, default=0,
                               help_text="Working days, excluding the Friday-Saturday weekend")
    reason = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="+")
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-start_date", "-id"]
        permissions = [("approve_leaverequest", "Can approve or reject leave requests")]

    def __str__(self):
        return f"{self.employee.full_name}: {self.get_leave_type_display()} {self.start_date:%d %b}-{self.end_date:%d %b %Y}"
