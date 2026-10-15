"""HR (lite): leave requests with an approval workflow. Oman weekend = Friday and Saturday."""
import datetime
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import LeaveRequest

WEEKEND = {4, 5}  # Python weekday(): Friday=4, Saturday=5


class LeaveError(ValueError):
    pass


def working_days(start, end):
    """Working days between two dates inclusive, excluding Friday and Saturday."""
    if end < start:
        return 0
    days = 0
    current = start
    while current <= end:
        if current.weekday() not in WEEKEND:
            days += 1
        current += datetime.timedelta(days=1)
    return days


def leave_taken(employee, year, leave_type=LeaveRequest.Type.ANNUAL):
    return employee.leave_requests.filter(
        leave_type=leave_type, status=LeaveRequest.Status.APPROVED, start_date__year=year
    ).aggregate(total=Sum("days"))["total"] or Decimal("0")


def leave_balance(employee, year=None):
    year = year or timezone.localdate().year
    return Decimal(employee.annual_leave_days) - leave_taken(employee, year)


@transaction.atomic
def submit_leave_request(employee, leave_type, start_date, end_date, reason="", user=None):
    if end_date < start_date:
        raise LeaveError("End date must be on or after the start date.")
    days = working_days(start_date, end_date)
    if days == 0:
        raise LeaveError("The selected period contains no working days.")
    overlapping = employee.leave_requests.filter(
        status__in=[LeaveRequest.Status.PENDING, LeaveRequest.Status.APPROVED],
        start_date__lte=end_date, end_date__gte=start_date,
    )
    if overlapping.exists():
        raise LeaveError("This period overlaps an existing leave request.")
    if leave_type == LeaveRequest.Type.ANNUAL and days > leave_balance(employee, start_date.year):
        raise LeaveError(f"Insufficient annual leave balance ({leave_balance(employee, start_date.year)} days left).")
    return LeaveRequest.objects.create(employee=employee, leave_type=leave_type, start_date=start_date,
                                       end_date=end_date, days=days, reason=reason, created_by=user)


def _decide(request, status, user, note):
    request = LeaveRequest.objects.select_for_update().get(pk=request.pk)
    if request.status != LeaveRequest.Status.PENDING:
        raise LeaveError("Only pending requests can be decided.")
    if user is not None and request.employee.user_id == user.pk:
        raise LeaveError("You cannot decide on your own leave request.")
    request.status = status
    request.decided_by = user
    request.decided_at = timezone.now()
    request.decision_note = note
    request.save(update_fields=["status", "decided_by", "decided_at", "decision_note", "updated_at"])
    return request


@transaction.atomic
def approve_leave(request, user=None, note=""):
    if request.leave_type == LeaveRequest.Type.ANNUAL and request.days > leave_balance(request.employee,
                                                                                       request.start_date.year):
        raise LeaveError("Approving would exceed the employee's annual leave balance.")
    return _decide(request, LeaveRequest.Status.APPROVED, user, note)


@transaction.atomic
def reject_leave(request, user=None, note=""):
    return _decide(request, LeaveRequest.Status.REJECTED, user, note)


@transaction.atomic
def cancel_leave(request, user=None):
    request = LeaveRequest.objects.select_for_update().get(pk=request.pk)
    if request.status not in (LeaveRequest.Status.PENDING, LeaveRequest.Status.APPROVED):
        raise LeaveError("This request can no longer be cancelled.")
    request.status = LeaveRequest.Status.CANCELLED
    request.save(update_fields=["status", "updated_at"])
    return request
