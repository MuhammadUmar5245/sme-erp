"""Test settings: fast password hashing, plain static storage."""
from .base import *  # noqa: F401,F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
ALLOWED_HOSTS = ["*"]
# Deterministic fallback so tests run without a .env (never used outside tests).
FIELD_ENCRYPTION_KEY = FIELD_ENCRYPTION_KEY or "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="  # noqa: F405
