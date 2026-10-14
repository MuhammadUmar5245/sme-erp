import datetime
from decimal import Decimal

from django import template
from django.db import models
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from core.money import q3

register = template.Library()

STATUS_COLOURS = {
    "DRAFT": "secondary",
    "PENDING": "warning",
    "APPROVED": "primary",
    "CONFIRMED": "primary",
    "RECEIVED": "info",
    "BILLED": "success",
    "POSTED": "primary",
    "PARTIAL": "warning",
    "PARTIALLY_PAID": "warning",
    "UNPAID": "danger",
    "OVERDUE": "danger",
    "PAID": "success",
    "INVOICED": "success",
    "REJECTED": "danger",
    "CANCELLED": "dark",
    "COMMITTED": "success",
    "FAILED": "danger",
    "VALIDATED": "info",
    "UPLOADED": "secondary",
    "MAPPED": "secondary",
}


@register.filter
def money(value, decimals=3):
    if value in (None, ""):
        return ""
    try:
        return f"{q3(value):,.{int(decimals)}f}"
    except Exception:  # pragma: no cover - defensive for odd template values
        return value


@register.filter
def pct(value, decimals=1):
    if value in (None, ""):
        return ""
    return f"{Decimal(str(value)):,.{int(decimals)}f}%"


@register.simple_tag
def status_badge(value, label=None):
    colour = STATUS_COLOURS.get(str(value).upper(), "secondary")
    return format_html('<span class="badge text-bg-{}">{}</span>', colour, label or value)


def _resolve(obj, path):
    value = obj
    field = None
    for part in path.split("."):
        if value is None:
            return None, None
        model_field = None
        if isinstance(value, models.Model):
            try:
                model_field = value._meta.get_field(part)
            except Exception:
                model_field = None
            if model_field is not None and getattr(model_field, "choices", None):
                display = getattr(value, f"get_{part}_display")()
                raw = getattr(value, part)
                return display, ("choice", raw, model_field)
        value = getattr(value, part, None)
        if callable(value) and not isinstance(value, models.Manager):
            value = value()
        field = model_field
    return value, field


@register.simple_tag
def cell(obj, path):
    """Render one table cell: choices, status badges, money, dates, booleans."""
    value, field = _resolve(obj, path)
    if isinstance(field, tuple) and field[0] == "choice":
        if path.split(".")[-1] == "status":
            return status_badge(field[1], value)
        return value
    if value is None or value == "":
        return mark_safe('<span class="text-muted">-</span>')
    if isinstance(value, bool):
        icon = "check-circle-fill text-success" if value else "x-circle text-muted"
        return format_html('<i class="bi bi-{}"></i>', icon)
    if isinstance(value, Decimal):
        decimals = getattr(field, "decimal_places", 3) if field is not None else 3
        if decimals == 3:
            return format_html('<span class="font-monospace">{}</span>', money(value))
        return f"{value:,.{decimals}f}"
    if isinstance(value, datetime.datetime):
        from django.utils import timezone

        return timezone.localtime(value).strftime("%d %b %Y %H:%M")
    if isinstance(value, datetime.date):
        return value.strftime("%d %b %Y")
    return value


@register.simple_tag
def detail_url(url_name, pk):
    return reverse(url_name, args=[pk])


@register.filter
def get_item(mapping, key):
    try:
        return mapping.get(key)
    except AttributeError:
        return None
