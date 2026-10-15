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


class SystemFeedback(models.Model):
    """User evaluation of the ERP itself (report 5.1.4): ratings, problems and suggestions."""

    class Area(models.TextChoices):
        GENERAL = "GENERAL", "ERP in general"
        SALES = "SALES", "Sales and CRM"
        INVENTORY = "INVENTORY", "Inventory and purchasing"
        FINANCE = "FINANCE", "Finance"
        HR = "HR", "HR"
        REPORTS = "REPORTS", "Dashboards and reports"
        POWER_BI = "POWER_BI", "Power BI"
        MOBILE = "MOBILE", "Mobile / tablet use"

    class Kind(models.TextChoices):
        RATING = "RATING", "Rating"
        PROBLEM = "PROBLEM", "Problem"
        SUGGESTION = "SUGGESTION", "Suggestion"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        RESOLVED = "RESOLVED", "Resolved"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    area = models.CharField(max_length=10, choices=Area.choices, default=Area.GENERAL)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.RATING)
    rating = models.PositiveSmallIntegerField(null=True, blank=True, help_text="1 (poor) to 5 (excellent)")
    comment = models.TextField(blank=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "user evaluation"
        constraints = [models.CheckConstraint(condition=models.Q(rating__isnull=True) | models.Q(rating__gte=1, rating__lte=5),
                                              name="system_feedback_rating_1_5")]

    def __str__(self):
        return f"{self.get_kind_display()} on {self.get_area_display()} ({self.rating or '-'})"


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
