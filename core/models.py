from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base for business records: creation/update timestamps and creator."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        editable=False,
    )

    class Meta:
        abstract = True


def money_field(**kwargs):
    """All money fields: DecimalField(14, 3) - OMR has 3 decimal places (baisa)."""
    kwargs.setdefault("max_digits", 14)
    kwargs.setdefault("decimal_places", 3)
    kwargs.setdefault("default", 0)
    return models.DecimalField(**kwargs)


def quantity_field(**kwargs):
    kwargs.setdefault("max_digits", 12)
    kwargs.setdefault("decimal_places", 3)
    kwargs.setdefault("default", 0)
    return models.DecimalField(**kwargs)
