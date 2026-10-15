import datetime
from decimal import Decimal

import pytest

from core.factories import EmployeeFactory
from hr import services
from hr.models import Employee, LeaveRequest

pytestmark = pytest.mark.django_db
SUN = datetime.date(2026, 3, 1)  # Sunday (first working day of the Omani week)


def test_working_days_exclude_friday_and_saturday():
    assert services.working_days(SUN, SUN + datetime.timedelta(days=6)) == 5
    assert services.working_days(datetime.date(2026, 3, 6), datetime.date(2026, 3, 7)) == 0  # Fri-Sat
    assert services.working_days(SUN, SUN - datetime.timedelta(days=1)) == 0


def test_submit_and_approve_leave(make_user):
    employee = EmployeeFactory()
    manager = make_user("mgr@alwadi.om", roles=["Manager"])
    request = services.submit_leave_request(employee, "ANNUAL", SUN, SUN + datetime.timedelta(days=11))
    assert request.days == 10 and request.status == LeaveRequest.Status.PENDING
    services.approve_leave(request, manager, "Enjoy")
    request.refresh_from_db()
    assert request.status == LeaveRequest.Status.APPROVED and request.decided_by == manager
    assert services.leave_balance(employee, 2026) == Decimal("20")


def test_overlap_and_balance_rules():
    employee = EmployeeFactory(annual_leave_days=5)
    services.submit_leave_request(employee, "SICK", SUN, SUN + datetime.timedelta(days=2))
    with pytest.raises(services.LeaveError):
        services.submit_leave_request(employee, "ANNUAL", SUN + datetime.timedelta(days=1), SUN + datetime.timedelta(days=3))
    with pytest.raises(services.LeaveError):
        services.submit_leave_request(employee, "ANNUAL", datetime.date(2026, 4, 5), datetime.date(2026, 4, 16))
    with pytest.raises(services.LeaveError):
        services.submit_leave_request(employee, "ANNUAL", SUN, SUN - datetime.timedelta(days=1))
    with pytest.raises(services.LeaveError):
        services.submit_leave_request(employee, "ANNUAL", datetime.date(2026, 3, 6), datetime.date(2026, 3, 7))


def test_cannot_approve_own_request(make_user):
    user = make_user("hr@alwadi.om", roles=["HROfficer"])
    employee = EmployeeFactory(user=user)
    request = services.submit_leave_request(employee, "SICK", SUN, SUN)
    with pytest.raises(services.LeaveError):
        services.approve_leave(request, user)


def test_reject_and_cancel():
    employee = EmployeeFactory()
    request = services.submit_leave_request(employee, "EMERGENCY", SUN, SUN)
    services.reject_leave(request, note="Peak season")
    request.refresh_from_db()
    assert request.status == LeaveRequest.Status.REJECTED
    with pytest.raises(services.LeaveError):
        services.approve_leave(request)
    with pytest.raises(services.LeaveError):
        services.cancel_leave(request)
    other = services.submit_leave_request(employee, "UNPAID", SUN + datetime.timedelta(days=7), SUN + datetime.timedelta(days=7))
    services.cancel_leave(other)
    other.refresh_from_db()
    assert other.status == LeaveRequest.Status.CANCELLED


def test_sensitive_fields_are_encrypted_at_rest():
    from django.db import connection

    employee = EmployeeFactory(national_id="12345678", bank_iban="OM810180000001299123456")
    with connection.cursor() as cursor:
        cursor.execute("SELECT national_id, bank_iban FROM hr_employee WHERE id = %s", [employee.pk])
        raw_id, raw_iban = cursor.fetchone()
    assert "12345678" not in raw_id and raw_id.startswith("gAAAA")
    assert "OM8101" not in raw_iban
    fresh = Employee.objects.get(pk=employee.pk)
    assert fresh.national_id == "12345678"
    assert fresh.national_id_masked.endswith("5678") and "1234" not in fresh.national_id_masked
