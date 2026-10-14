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
