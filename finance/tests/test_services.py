import datetime
from decimal import Decimal

import pytest

from finance import chart, services
from finance.models import Account, JournalEntry

pytestmark = pytest.mark.django_db
TODAY = datetime.date(2026, 5, 10)


def test_chart_of_accounts_is_seeded():
    assert Account.objects.filter(code=chart.VAT_OUTPUT, account_type="LIABILITY").exists()
    assert Account.objects.count() == len(chart.CHART_OF_ACCOUNTS)
    assert services.seed_chart_of_accounts() == 0  # idempotent


def test_balanced_entry_is_posted():
    entry = services.post_journal(TODAY, "Capital injection", [(chart.BANK, 1000, 0), (chart.CAPITAL, 0, 1000)])
    assert entry.number.startswith("JE-2026-")
    assert entry.total_debit == entry.total_credit == Decimal("1000.000")


def test_unbalanced_entry_is_rejected():
    with pytest.raises(services.UnbalancedEntry):
        services.post_journal(TODAY, "Bad", [(chart.BANK, 100, 0), (chart.CAPITAL, 0, 99)])
    assert not JournalEntry.objects.exists()


def test_line_with_both_sides_or_negative_is_rejected():
    with pytest.raises(services.UnbalancedEntry):
        services.post_journal(TODAY, "Bad", [(chart.BANK, 10, 10)])
    with pytest.raises(services.UnbalancedEntry):
        services.post_journal(TODAY, "Bad", [(chart.BANK, -10, 0), (chart.CAPITAL, 0, -10)])
    with pytest.raises(services.UnbalancedEntry):
        services.post_journal(TODAY, "Empty", [(chart.BANK, 0, 0)])


def test_reverse_journal_nets_to_zero():
    entry = services.post_journal(TODAY, "x", [(chart.BANK, 50, 0), (chart.CAPITAL, 0, 50)])
    services.reverse_journal(entry, TODAY)
    assert services.account_balance(chart.BANK) == 0


def test_expense_posts_vat_input_and_bank():
    expense = services.record_expense(TODAY, "6300", "Shell Oman", "Fuel for delivery vans", Decimal("100"))
    assert expense.vat_amount == Decimal("5.000") and expense.total == Decimal("105.000")
    assert services.account_balance("6300") == Decimal("100.000")
    assert services.account_balance(chart.VAT_INPUT) == Decimal("5.000")
    assert services.account_balance(chart.BANK) == Decimal("-105.000")


def test_expense_requires_expense_account():
    with pytest.raises(ValueError):
        services.record_expense(TODAY, chart.BANK, "x", "x", 10)
    with pytest.raises(ValueError):
        services.record_expense(TODAY, "6300", "x", "x", 0)


def test_trial_balance_balances_and_pnl():
    services.post_journal(TODAY, "Capital", [(chart.BANK, 5000, 0), (chart.CAPITAL, 0, 5000)])
    services.post_journal(TODAY, "Cash sale", [(chart.CASH, 1050, 0), (chart.SALES, 0, 1000), (chart.VAT_OUTPUT, 0, 50)])
    services.post_journal(TODAY, "COGS", [(chart.COGS, 600, 0), (chart.INVENTORY, 0, 600)])
    services.record_expense(TODAY, "6100", "Landlord", "Rent", 200)
    tb = services.trial_balance(TODAY)
    assert tb["balanced"] and tb["total_debit"] == tb["total_credit"]
    pnl = services.profit_and_loss(TODAY.replace(day=1), TODAY)
    assert pnl["total_income"] == Decimal("1000.000")
    assert pnl["gross_profit"] == Decimal("400.000")
    assert pnl["gross_margin_pct"] == Decimal("40")
    assert pnl["net_profit"] == Decimal("200.000")


def test_vat_return_nets_output_and_input():
    services.post_journal(TODAY, "Sale", [(chart.ACCOUNTS_RECEIVABLE, 2100, 0), (chart.SALES, 0, 2000),
                                          (chart.VAT_OUTPUT, 0, 100)])
    services.record_expense(TODAY, "6200", "Nama", "Electricity", 400)
    report = services.vat_return(TODAY.replace(day=1), TODAY)
    assert report["output_vat"] == Decimal("100.000")
    assert report["input_vat"] == Decimal("20.000")
    assert report["net_vat_payable"] == Decimal("80.000")
    assert report["taxable_sales"] == Decimal("2000.000")


def test_opening_balances_balance_through_equity():
    entry = services.post_opening_balances(TODAY, [(chart.BANK, 12000, 0), (chart.ACCOUNTS_PAYABLE, 0, 3000)])
    assert entry.total_debit == entry.total_credit
    assert services.account_balance(chart.OPENING_BALANCE_EQUITY) == Decimal("9000.000")


def test_cash_flow_and_month_bounds():
    services.post_journal(TODAY, "In", [(chart.BANK, 300, 0), (chart.SALES, 0, 300)])
    services.record_expense(TODAY, "6900", "x", "Misc", 100)
    flow = services.cash_flow_summary(TODAY.replace(day=1), TODAY)
    assert flow["cash_in"] == Decimal("300.000") and flow["cash_out"] == Decimal("105.000")
    assert services.month_bounds(datetime.date(2026, 2, 14)) == (datetime.date(2026, 2, 1), datetime.date(2026, 2, 28))
