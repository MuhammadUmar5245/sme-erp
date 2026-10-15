"""The demo seed must produce consistent, deterministic data (run here at a small scale)."""
import datetime
from decimal import Decimal
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.db import transaction
from django.db.models import Min, Sum

from core.seed.generator import DemoSeeder, add_months
from crm.models import Customer, Feedback
from finance import chart
from finance.services import account_balance, trial_balance
from hr.models import Employee
from inventory.models import Product, StockMovement
from sales.models import Invoice, Payment

pytestmark = pytest.mark.django_db
TODAY = datetime.date(2026, 4, 30)  # covers Ramadan and Eid al-Fitr 2026


@pytest.fixture
def seeded():
    seeder = DemoSeeder(today=TODAY, months=3, target_invoices=250, seed=42, log=lambda *a: None)
    summary = seeder.run()
    return seeder, summary


def test_master_data_volumes(seeded):
    seeder, summary = seeded
    assert Product.objects.count() == 120
    assert Product.objects.values("category").distinct().count() == 8
    assert summary["Suppliers"] == 40
    assert Customer.objects.exclude(code="CASH").count() == 300
    assert set(Customer.objects.exclude(code="CASH").values_list("city", flat=True)) == {
        "Muscat", "Seeb", "Sohar", "Salalah", "Nizwa", "Sur"}
    assert Employee.objects.count() == 45
    roles = {g for u in get_user_model().objects.all() for g in u.role_names}
    assert {"Admin", "Manager", "Accountant", "SalesOfficer", "Storekeeper", "HROfficer", "Viewer"} <= roles


def test_transactions_are_consistent(seeded):
    seeder, _ = seeded
    assert 200 <= Invoice.objects.count() <= 300
    assert Invoice.objects.aggregate(d=Min("invoice_date"))["d"] >= seeder.start
    assert trial_balance()["balanced"]
    # Stock is never negative in any warehouse.
    negatives = (StockMovement.objects.values("product", "warehouse").annotate(q=Sum("quantity"))
                 .filter(q__lt=0))
    assert not negatives.exists()
    # The AR control account equals the open invoice balances.
    open_balance = sum((i.balance_due for i in Invoice.objects.all()), Decimal(0))
    assert account_balance(chart.ACCOUNTS_RECEIVABLE) == open_balance
    assert Payment.objects.exists() and Feedback.objects.exists()
    assert Invoice.objects.filter(source="POS").exists()


def test_ramadan_is_busier_than_baseline(seeded):
    ramadan = Invoice.objects.filter(invoice_date__range=(datetime.date(2026, 2, 18), datetime.date(2026, 3, 19)))
    baseline = Invoice.objects.filter(invoice_date__range=(datetime.date(2026, 4, 1), datetime.date(2026, 4, 30)))
    per_day = lambda qs, days: qs.count() / days  # noqa: E731
    assert per_day(ramadan, 30) > per_day(baseline, 30)


class _Rollback(Exception):
    pass


def test_seed_is_deterministic():
    summaries = []
    for _ in range(2):
        try:
            with transaction.atomic():
                summaries.append(DemoSeeder(today=TODAY, months=1, target_invoices=60, seed=42,
                                            log=lambda *a: None).run())
                raise _Rollback
        except _Rollback:
            pass
    assert summaries[0] == summaries[1]


def test_command_requires_reset_when_data_exists(seeded):
    with pytest.raises(CommandError):
        call_command("seed_demo", stdout=StringIO())


def test_add_months():
    assert add_months(datetime.date(2026, 10, 31), -18) == datetime.date(2025, 4, 30)
    assert add_months(datetime.date(2024, 3, 31), -1) == datetime.date(2024, 2, 29)
