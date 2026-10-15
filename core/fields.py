"""Encrypted model field for sensitive personal data at rest (national ID, IBAN).

Values are encrypted with Fernet (AES-128-CBC + HMAC-SHA256) using FIELD_ENCRYPTION_KEY from .env
before they reach PostgreSQL, so database dumps and backups do not expose them in clear text.
"""
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models


def _fernet():
    key = getattr(settings, "FIELD_ENCRYPTION_KEY", "")
    if not key:
        raise ImproperlyConfigured("FIELD_ENCRYPTION_KEY is not set (see .env.example).")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return token  # legacy plain-text value


class EncryptedTextField(models.TextField):
    description = "Text encrypted at rest with Fernet"

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        return decrypt(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value in (None, ""):
            return value
        return encrypt(str(value))


def mask(value, visible=4):
    if not value:
        return ""
    return "•" * max(len(value) - visible, 0) + value[-visible:]
