import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from accounts import services
from accounts.roles import ROLES

pytestmark = pytest.mark.django_db


def test_data_migration_creates_all_seven_roles():
    assert set(Group.objects.filter(name__in=ROLES).values_list("name", flat=True)) == set(ROLES)


def test_admin_role_has_every_permission():
    from django.contrib.auth.models import Permission

    admin = Group.objects.get(name="Admin")
    assert admin.permissions.count() == Permission.objects.count()


def test_viewer_is_read_only_on_users_and_audit(make_user):
    viewer = make_user("viewer@alwadi.om", roles=["Viewer"])
    assert not viewer.has_perm("accounts.view_auditlog")
    assert not viewer.has_perm("accounts.add_user")
    assert viewer.has_perm("hr.view_department")
    assert not viewer.has_perm("hr.add_department")


def test_hr_officer_manages_departments_only(make_user):
    hr = make_user("hr@alwadi.om", roles=["HROfficer"])
    assert hr.has_perm("hr.add_department")
    assert not hr.has_perm("accounts.view_user")


def test_sync_is_idempotent():
    before = Group.objects.get(name="Manager").permissions.count()
    services.sync_role_permissions()
    services.sync_role_permissions()
    assert Group.objects.get(name="Manager").permissions.count() == before


def test_menu_hides_administration_for_viewer(client, make_user):
    client.force_login(make_user("viewer@alwadi.om", roles=["Viewer"]))
    html = client.get(reverse("core:dashboard")).content.decode()
    assert reverse("accounts:user_list") not in html
    assert reverse("accounts:audit_list") not in html


def test_menu_shows_administration_for_admin(client, make_user):
    user = make_user("boss@alwadi.om", roles=["Admin"])
    _verified_login(client, user)
    html = client.get(reverse("core:dashboard")).content.decode()
    assert reverse("accounts:user_list") in html
    assert reverse("accounts:audit_list") in html


def test_user_pages_forbidden_without_permission(client, make_user):
    client.force_login(make_user("sales@alwadi.om", roles=["SalesOfficer"]))
    assert client.get(reverse("accounts:user_list")).status_code == 403
    assert client.get(reverse("accounts:audit_list")).status_code == 403


def test_api_users_endpoint_enforces_roles(client, make_user):
    client.force_login(make_user("viewer@alwadi.om", roles=["Viewer"]))
    assert client.get("/api/v1/accounts/users/").status_code == 403
    assert client.get("/api/v1/accounts/audit-logs/").status_code == 403


def test_api_requires_authentication(client):
    assert client.get("/api/v1/accounts/users/").status_code in (401, 403)


def _verified_login(client, user):
    """Log in a user whose role requires 2FA, with a confirmed TOTP device and verified session."""
    from django_otp.oath import totp
    from django_otp.plugins.otp_totp.models import TOTPDevice

    device = TOTPDevice.objects.create(user=user, name="test", confirmed=True)
    client.force_login(user)
    token = totp(device.bin_key, device.step, device.t0, device.digits, device.drift)
    response = client.post(reverse("accounts:2fa_verify"), {"token": f"{token:06d}"})
    assert response.status_code == 302
    return device
