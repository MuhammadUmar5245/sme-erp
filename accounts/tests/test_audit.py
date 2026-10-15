import pytest
from django.urls import reverse

from accounts import audit
from accounts.models import AuditLog
from conftest import TEST_PASSWORD
from hr.models import Department

pytestmark = pytest.mark.django_db


def test_create_update_delete_are_logged_with_changes():
    dept = Department.objects.create(code="SAL", name="Sales")
    created = AuditLog.objects.get(action="create", model="hr.department", object_id=str(dept.pk))
    assert created.changes["name"] == [None, "Sales"]

    dept.name = "Sales & Marketing"
    dept.save()
    updated = AuditLog.objects.get(action="update", model="hr.department")
    assert updated.changes == {"name": ["Sales", "Sales & Marketing"]}

    pk = dept.pk
    dept.delete()
    assert AuditLog.objects.filter(action="delete", model="hr.department", object_id=str(pk)).exists()


def test_save_without_changes_is_not_logged():
    dept = Department.objects.create(code="FIN", name="Finance")
    dept.save()
    assert not AuditLog.objects.filter(action="update", model="hr.department").exists()


def test_disabled_context_skips_logging():
    with audit.disabled():
        Department.objects.create(code="OPS", name="Operations")
    assert not AuditLog.objects.filter(model="hr.department").exists()


def test_request_user_and_ip_are_captured(client, make_user):
    hr_user = make_user("hr@alwadi.om", roles=["HROfficer"])
    from django.test import RequestFactory

    from accounts.middleware import CurrentRequestMiddleware

    request = RequestFactory().post("/x", HTTP_X_FORWARDED_FOR="10.20.30.40")
    request.user = hr_user
    CurrentRequestMiddleware(lambda r: Department.objects.create(code="WH", name="Warehouse"))(request)
    log = AuditLog.objects.get(model="hr.department", action="create")
    assert log.user == hr_user
    assert log.user_email == "hr@alwadi.om"
    assert log.ip_address == "10.20.30.40"


def test_password_changes_are_not_stored(make_user):
    user = make_user("someone@alwadi.om")
    user.set_password("Another-Strong-Pass-1")
    user.save()
    for log in AuditLog.objects.filter(model="accounts.user"):
        assert "password" not in log.changes


def test_login_and_failed_login_are_logged(client, make_user):
    make_user("clerk@alwadi.om", roles=["Viewer"])
    client.post("/accounts/login/", {"username": "clerk@alwadi.om", "password": "bad-password-xx"})
    client.post("/accounts/login/", {"username": "clerk@alwadi.om", "password": TEST_PASSWORD})
    assert AuditLog.objects.filter(action="login_failed", user_email="clerk@alwadi.om").exists()
    assert AuditLog.objects.filter(action="login", user_email="clerk@alwadi.om").exists()


def test_audit_viewer_lists_entries_for_admin(client, admin_user):
    Department.objects.create(code="HR", name="Human Resources")
    from django_otp.plugins.otp_totp.models import TOTPDevice

    TOTPDevice.objects.create(user=admin_user, name="x", confirmed=True)
    client.force_login(admin_user)
    session = client.session
    device = TOTPDevice.objects.get(user=admin_user)
    session["otp_device_id"] = device.persistent_id
    session.save()
    response = client.get(reverse("accounts:audit_list"))
    assert response.status_code == 200
    assert b"Human Resources" in response.content
    entry = AuditLog.objects.filter(model="hr.department").first()
    assert client.get(reverse("accounts:audit_detail", args=[entry.pk])).status_code == 200


def test_audit_log_is_read_only_in_api(client, admin_user):
    from rest_framework.test import APIClient

    api = APIClient()
    api.force_authenticate(admin_user)
    assert api.post("/api/v1/accounts/audit-logs/", {}).status_code == 405
