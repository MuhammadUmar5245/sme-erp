import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from accounts import services

pytestmark = pytest.mark.django_db
User = get_user_model()


def test_create_user_service_assigns_roles_and_staff_flag():
    user = services.create_user("ali@alwadi.om", "Muscat-Strong-Pass-1", roles=["Admin"], first_name="Ali")
    assert user.role_names == ["Admin"]
    assert user.is_staff
    assert user.check_password("Muscat-Strong-Pass-1")


def test_create_user_service_rejects_weak_password():
    with pytest.raises(ValidationError):
        services.create_user("weak@alwadi.om", "short", roles=["Viewer"])


def test_set_roles_removes_staff_flag_when_admin_role_dropped():
    user = services.create_user("ali@alwadi.om", "Muscat-Strong-Pass-1", roles=["Admin"])
    services.set_roles(user, ["Viewer"])
    user.refresh_from_db()
    assert not user.is_staff
    assert user.role_names == ["Viewer"]


def test_requires_2fa_only_for_admin_and_accountant(make_user):
    assert make_user("a@alwadi.om", roles=["Admin"]).requires_2fa
    assert make_user("b@alwadi.om", roles=["Accountant"]).requires_2fa
    assert not make_user("c@alwadi.om", roles=["SalesOfficer"]).requires_2fa


def test_admin_api_creates_user_with_roles(admin_user):
    api = APIClient()
    api.force_authenticate(admin_user)
    response = api.post(
        "/api/v1/accounts/users/",
        {"email": "new@alwadi.om", "password": "Brand-New-Pass-2026", "roles": ["Storekeeper"]},
        format="json",
    )
    assert response.status_code == 201, response.content
    assert User.objects.get(email="new@alwadi.om").role_names == ["Storekeeper"]


def test_user_form_ui_creates_user(client, admin_user):
    from django_otp.plugins.otp_totp.models import TOTPDevice

    device = TOTPDevice.objects.create(user=admin_user, name="x", confirmed=True)
    client.force_login(admin_user)
    session = client.session
    session["otp_device_id"] = device.persistent_id
    session.save()
    response = client.post(
        "/accounts/users/new/",
        {"email": "Clerk@AlWadi.om", "first_name": "Sara", "password": "Clerk-Strong-Pass-1",
         "roles": ["SalesOfficer"], "is_active": "on"},
    )
    assert response.status_code == 302, response.content
    user = User.objects.get(email="clerk@alwadi.om")
    assert user.role_names == ["SalesOfficer"]


def test_user_list_detail_and_profile_pages_render(client, admin_user, make_user):
    from conftest import login_verified

    other = make_user("store@alwadi.om", roles=["Storekeeper"])
    login_verified(client, admin_user)
    assert b"store@alwadi.om" in client.get("/accounts/users/?q=store").content
    assert client.get(f"/accounts/users/{other.pk}/").status_code == 200
    assert client.get(f"/accounts/users/{other.pk}/edit/").status_code == 200
    assert client.get("/accounts/profile/").status_code == 200
    htmx = client.get("/accounts/users/?q=store", HTTP_HX_REQUEST="true", HTTP_HX_TARGET="list-table")
    assert b"<html" not in htmx.content and b"store@alwadi.om" in htmx.content
