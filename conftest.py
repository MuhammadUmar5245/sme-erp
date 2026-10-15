"""Shared pytest fixtures."""
import pytest
from django.contrib.auth import get_user_model

TEST_PASSWORD = "Str0ng-Passw0rd!2024"


@pytest.fixture
def password():
    return TEST_PASSWORD


@pytest.fixture
def make_user(db):
    """Create a user, optionally in role groups: make_user("x@y.om", roles=["Manager"])."""

    def _make(email="user@alwadi.om", roles=(), **extra):
        from django.contrib.auth.models import Group

        user = get_user_model().objects.create_user(email=email, password=TEST_PASSWORD, **extra)
        for role in roles:
            group, _ = Group.objects.get_or_create(name=role)
            user.groups.add(group)
        return user

    return _make


@pytest.fixture
def admin_user(db):
    return get_user_model().objects.create_superuser(email="admin@alwadi.om", password=TEST_PASSWORD)


def login_verified(client, user):
    """Log in with a confirmed TOTP device and an OTP-verified session (passes 2FA enforcement)."""
    from django_otp.plugins.otp_totp.models import TOTPDevice

    device = TOTPDevice.objects.filter(user=user, confirmed=True).first() or TOTPDevice.objects.create(
        user=user, name="test", confirmed=True
    )
    client.force_login(user)
    session = client.session
    session["otp_device_id"] = device.persistent_id
    session.save()
    return client


@pytest.fixture
def login(client):
    """login(user) -> Django test client logged in as that user with 2FA satisfied."""
    return lambda user: login_verified(client, user)


@pytest.fixture
def api(db):
    """api(user) -> DRF APIClient authenticated as user (token-style, bypasses session 2FA)."""
    from rest_framework.test import APIClient

    def _api(user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    return _api
