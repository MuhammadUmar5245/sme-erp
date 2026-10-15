"""Document numbering: INV-2026-000001, PO-2026-000014 ... unique and sequential per prefix and year."""
import datetime

from django.db import transaction
from django.utils import timezone


def next_number(prefix, date=None):
    date = date or timezone.localdate()
    year = date.year if isinstance(date, (datetime.date, datetime.datetime)) else int(date)
    from .models import Sequence

    with transaction.atomic():
        seq, _ = Sequence.objects.select_for_update().get_or_create(name=f"{prefix}-{year}")
        seq.last_value += 1
        seq.save(update_fields=["last_value"])
        return f"{prefix}-{year}-{seq.last_value:06d}"
