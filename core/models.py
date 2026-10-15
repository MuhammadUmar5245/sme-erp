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


class Sequence(models.Model):
    """Gap-free document number counters (one row per prefix and year), locked with SELECT FOR UPDATE."""

    name = models.CharField(max_length=30, unique=True)
    last_value = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name}: {self.last_value}"


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
