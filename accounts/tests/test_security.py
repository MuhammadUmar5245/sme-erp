"""Lockout (django-axes), password policy, session timeout and TOTP 2FA enforcement."""
import pytest
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.urls import reverse
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from accounts import services
from conftest import TEST_PASSWORD

pytestmark = pytest.mark.django_db

LOGIN = "/accounts/login/"


def _login(client, email, password):
    return client.post(LOGIN, {"username": email, "password": password})


def _code(device):
    return f"{totp(device.bin_key, device.step, device.t0, device.digits, device.drift):06d}"


def test_successful_login_redirects_to_dashboard(client, make_user):
    make_user("clerk@alwadi.om", roles=["Viewer"])
    response = _login(client, "clerk@alwadi.om", TEST_PASSWORD)
    assert response.status_code == 302
    assert response["Location"] == reverse("core:dashboard")


def test_login_is_case_insensitive_on_email(client, make_user):
    make_user("clerk@alwadi.om", roles=["Viewer"])
    assert _login(client, "Clerk@AlWadi.om", TEST_PASSWORD).status_code == 302


def test_account_locked_after_five_failed_logins(client, make_user):
    user = make_user("clerk@alwadi.om", roles=["Viewer"])
    for _ in range(settings.AXES_FAILURE_LIMIT):
        _login(client, "clerk@alwadi.om", "wrong-password-123")
    # Even the correct password is refused while locked.
    response = _login(client, "clerk@alwadi.om", TEST_PASSWORD)
    assert response.status_code == 429
    assert b"locked" in response.content.lower()
    assert services.is_locked_out(user)


def test_four_failures_do_not_lock(client, make_user):
    make_user("clerk@alwadi.om", roles=["Viewer"])
    for _ in range(settings.AXES_FAILURE_LIMIT - 1):
        _login(client, "clerk@alwadi.om", "wrong-password-123")
    assert _login(client, "clerk@alwadi.om", TEST_PASSWORD).status_code == 302


def test_admin_can_unlock_account(client, make_user):
    user = make_user("clerk@alwadi.om", roles=["Viewer"])
    for _ in range(settings.AXES_FAILURE_LIMIT):
        _login(client, "clerk@alwadi.om", "wrong-password-123")
    services.unlock_user(user)
    assert not services.is_locked_out(user)
    assert _login(client, "clerk@alwadi.om", TEST_PASSWORD).status_code == 302


def test_password_policy_requires_12_characters():
    with pytest.raises(ValidationError):
        validate_password("Short1!aa")
    validate_password("Muscat-Warehouse-2026")


def test_session_idle_timeout_is_30_minutes():
    assert settings.SESSION_COOKIE_AGE == 1800
    assert settings.SESSION_SAVE_EVERY_REQUEST is True


def test_accountant_without_device_is_sent_to_enrolment(client, make_user):
    client.force_login(make_user("acc@alwadi.om", roles=["Accountant"]))
    response = client.get(reverse("core:dashboard"))
    assert response.status_code == 302
    assert response["Location"].startswith(reverse("accounts:2fa_setup"))


def test_viewer_without_device_is_not_forced(client, make_user):
    client.force_login(make_user("viewer@alwadi.om", roles=["Viewer"]))
    assert client.get(reverse("core:dashboard")).status_code == 200


def test_enrolment_with_qr_and_valid_code_activates_2fa(client, make_user):
    user = make_user("acc@alwadi.om", roles=["Accountant"])
    client.force_login(user)
    page = client.get(reverse("accounts:2fa_setup"))
    assert page.status_code == 200
    assert b"<svg" in page.content
    device = TOTPDevice.objects.get(user=user, confirmed=False)
    response = client.post(reverse("accounts:2fa_setup"), {"token": _code(device)})
    assert response.status_code == 302
    device.refresh_from_db()
    assert device.confirmed
    assert client.get(reverse("core:dashboard")).status_code == 200


def test_enrolment_rejects_wrong_code(client, make_user):
    user = make_user("acc@alwadi.om", roles=["Accountant"])
    client.force_login(user)
    client.get(reverse("accounts:2fa_setup"))
    response = client.post(reverse("accounts:2fa_setup"), {"token": "000000"})
    assert response.status_code == 200
    assert not TOTPDevice.objects.filter(user=user, confirmed=True).exists()


def test_user_with_device_must_verify_after_password(client, make_user):
    user = make_user("viewer@alwadi.om", roles=["Viewer"])
    device = TOTPDevice.objects.create(user=user, name="phone", confirmed=True)
    _login(client, "viewer@alwadi.om", TEST_PASSWORD)
    response = client.get(reverse("core:dashboard"))
    assert response["Location"].startswith(reverse("accounts:2fa_verify"))
    client.post(reverse("accounts:2fa_verify"), {"token": _code(device)})
    assert client.get(reverse("core:dashboard")).status_code == 200


def test_api_session_without_2fa_gets_403(client, make_user):
    client.force_login(make_user("acc@alwadi.om", roles=["Accountant"]))
    response = client.get("/api/v1/accounts/users/")
    assert response.status_code == 403


def test_token_endpoint_requires_otp_for_enrolled_user(client, make_user):
    user = make_user("acc@alwadi.om", roles=["Accountant"])
    device = TOTPDevice.objects.create(user=user, name="phone", confirmed=True)
    body = {"email": "acc@alwadi.om", "password": TEST_PASSWORD}
    assert client.post("/api/v1/auth/token/", body).status_code == 400
    response = client.post("/api/v1/auth/token/", {**body, "otp": _code(device)})
    assert response.status_code == 200
    assert len(response.json()["token"]) == 40


def test_token_endpoint_refuses_mandatory_role_without_device(client, make_user):
    make_user("acc@alwadi.om", roles=["Accountant"])
    response = client.post("/api/v1/auth/token/", {"email": "acc@alwadi.om", "password": TEST_PASSWORD})
    assert response.status_code == 403


def test_reset_two_factor_removes_devices(make_user):
    user = make_user("viewer@alwadi.om", roles=["Viewer"])
    TOTPDevice.objects.create(user=user, name="phone", confirmed=True)
    assert services.has_two_factor(user)
    services.reset_two_factor(user)
    assert not services.has_two_factor(user)
