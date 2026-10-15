"""Finance business logic: double-entry postings and financial reports.

Every automatic posting from other modules (invoices, payments, credit notes, goods receipts,
supplier bills, supplier payments, expenses, stock adjustments) goes through `post_journal`, which
refuses unbalanced entries.
"""
import datetime
from collections import OrderedDict
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from core.money import q3, vat_amount
from core.numbering import next_number

from . import chart
from .models import Account, Expense, JournalEntry, JournalLine

ZERO = Decimal("0.000")


class UnbalancedEntry(ValueError):
    pass


def account(code):
    return Account.objects.get(code=code)


def seed_chart_of_accounts():
    """Idempotently create the standard chart of accounts."""
    created = 0
    for code, name, account_type, system in chart.CHART_OF_ACCOUNTS:
        _, was_created = Account.objects.get_or_create(
            code=code, defaults={"name": name, "account_type": account_type, "is_system": system}
        )
        created += int(was_created)
    return created


@transaction.atomic
def post_journal(entry_date, description, lines, source_type=JournalEntry.Source.MANUAL, source_id=None,
                 reference="", user=None):
    """Create a balanced journal entry.

    lines: iterable of (account_code_or_Account, debit, credit[, description]). Zero lines are skipped.
    """
    prepared = []
    total_debit = total_credit = ZERO
    for line in lines:
        acct, debit, credit = line[0], q3(line[1]), q3(line[2])
        memo = line[3] if len(line) > 3 else ""
        if debit < 0 or credit < 0:
            raise UnbalancedEntry("Debit and credit amounts must not be negative.")
        if debit and credit:
            raise UnbalancedEntry("A journal line is either a debit or a credit, not both.")
        if not debit and not credit:
            continue
        if not isinstance(acct, Account):
            acct = account(acct)
        prepared.append(JournalLine(account=acct, debit=debit, credit=credit, description=memo[:200]))
        total_debit += debit
        total_credit += credit
    if not prepared:
        raise UnbalancedEntry("A journal entry needs at least one non-zero line.")
    if total_debit != total_credit:
        raise UnbalancedEntry(f"Entry does not balance: debit {total_debit} vs credit {total_credit}.")
    entry = JournalEntry.objects.create(
        number=next_number("JE", entry_date),
        entry_date=entry_date,
        description=description[:255],
        source_type=source_type,
        source_id=source_id,
        reference=reference,
        created_by=user,
    )
    for line in prepared:
        line.entry = entry
    JournalLine.objects.bulk_create(prepared)
    return entry


@transaction.atomic
def reverse_journal(entry, entry_date=None, user=None):
    lines = [(l.account, l.credit, l.debit, f"Reversal: {l.description}") for l in entry.lines.all()]
    return post_journal(entry_date or timezone.localdate(), f"Reversal of {entry.number}", lines,
                        entry.source_type, entry.source_id, entry.number, user)


def post_stock_adjustment(movement, user=None):
    """Dr/Cr Inventory against Inventory adjustments for a stock count correction."""
    value = q3(abs(movement.quantity) * movement.unit_cost)
    if not value:
        return None
    if movement.quantity > 0:
        lines = [(chart.INVENTORY, value, 0), (chart.INVENTORY_ADJUSTMENTS, 0, value)]
    else:
        lines = [(chart.INVENTORY_ADJUSTMENTS, value, 0), (chart.INVENTORY, 0, value)]
    return post_journal(timezone.localtime(movement.movement_date).date(),
                        f"Stock adjustment {movement.reference_no} {movement.product.sku}", lines,
                        JournalEntry.Source.STOCK_ADJUSTMENT, movement.pk, movement.reference_no, user)


@transaction.atomic
def record_expense(expense_date, account_code, payee, description, amount, vat_rate=Decimal("5"),
                   paid_from=Expense.PaidFrom.BANK, reference="", user=None):
    """Operating expense paid from cash or bank: Dr expense + Dr VAT input / Cr cash-or-bank."""
    exp_account = account_code if isinstance(account_code, Account) else account(account_code)
    if exp_account.account_type != Account.Type.EXPENSE:
        raise ValueError("Expenses must be posted to an expense account.")
    amount = q3(amount)
    if amount <= 0:
        raise ValueError("Expense amount must be positive.")
    vat = vat_amount(amount, vat_rate)
    expense = Expense.objects.create(
        number=next_number("EXP", expense_date), expense_date=expense_date, account=exp_account, payee=payee,
        description=description, amount=amount, vat_amount=vat, total=amount + vat, paid_from=paid_from,
        reference=reference, created_by=user,
    )
    expense.journal_entry = post_journal(
        expense_date, f"Expense {expense.number} - {payee}",
        [(exp_account, amount, 0, description), (chart.VAT_INPUT, vat, 0), (paid_from, 0, amount + vat)],
        JournalEntry.Source.EXPENSE, expense.pk, expense.number, user,
    )
    expense.save(update_fields=["journal_entry"])
    return expense


@transaction.atomic
def post_opening_balances(entry_date, balances, user=None):
    """Opening GL balances from a legacy system. balances: [(account_code, debit, credit)].

    Any difference is booked to Opening balance equity so the entry always balances.
    """
    lines = [(code, debit, credit, "Opening balance") for code, debit, credit in balances]
    diff = sum(q3(d) for _, d, _c in balances) - sum(q3(c) for _, _d, c in balances)
    if diff > 0:
        lines.append((chart.OPENING_BALANCE_EQUITY, 0, diff, "Opening balance difference"))
    elif diff < 0:
        lines.append((chart.OPENING_BALANCE_EQUITY, -diff, 0, "Opening balance difference"))
    return post_journal(entry_date, "Opening balances (data migration)", lines, JournalEntry.Source.OPENING,
                        user=user)


# ---- Reports ---------------------------------------------------------------------------------


def _line_filter(date_from=None, date_to=None):
    condition = Q()
    if date_from:
        condition &= Q(entry__entry_date__gte=date_from)
    if date_to:
        condition &= Q(entry__entry_date__lte=date_to)
    return condition


def account_balance(code, date_from=None, date_to=None):
    """Signed balance in the account's normal direction."""
    acct = account(code)
    totals = JournalLine.objects.filter(_line_filter(date_from, date_to), account=acct).aggregate(
        d=Sum("debit"), c=Sum("credit"))
    debit, credit = totals["d"] or ZERO, totals["c"] or ZERO
    return debit - credit if acct.normal_debit else credit - debit


def trial_balance(as_of=None, date_from=None):
    """Rows of (account, debit balance, credit balance); totals must be equal."""
    rows = []
    sums = (
        JournalLine.objects.filter(_line_filter(date_from, as_of))
        .values("account_id")
        .annotate(d=Sum("debit"), c=Sum("credit"))
    )
    by_account = {row["account_id"]: row for row in sums}
    total_debit = total_credit = ZERO
    for acct in Account.objects.all():
        row = by_account.get(acct.pk)
        if not row:
            continue
        net = (row["d"] or ZERO) - (row["c"] or ZERO)
        debit, credit = (net, ZERO) if net >= 0 else (ZERO, -net)
        if not debit and not credit:
            continue
        rows.append({"account": acct, "debit": debit, "credit": credit})
        total_debit += debit
        total_credit += credit
    return {"rows": rows, "total_debit": total_debit, "total_credit": total_credit,
            "balanced": total_debit == total_credit, "as_of": as_of}


def profit_and_loss(date_from, date_to):
    sums = {
        row["account_id"]: row
        for row in JournalLine.objects.filter(_line_filter(date_from, date_to))
        .filter(account__account_type__in=[Account.Type.INCOME, Account.Type.EXPENSE])
        .values("account_id")
        .annotate(d=Sum("debit"), c=Sum("credit"))
    }
    income, expenses = [], []
    for acct in Account.objects.filter(account_type__in=[Account.Type.INCOME, Account.Type.EXPENSE]):
        row = sums.get(acct.pk)
        if not row:
            continue
        d, c = row["d"] or ZERO, row["c"] or ZERO
        if acct.account_type == Account.Type.INCOME:
            income.append({"account": acct, "amount": c - d})
        else:
            expenses.append({"account": acct, "amount": d - c})
    total_income = sum((r["amount"] for r in income), ZERO)
    cogs = sum((r["amount"] for r in expenses if r["account"].code.startswith("5")), ZERO)
    total_expenses = sum((r["amount"] for r in expenses), ZERO)
    gross_profit = total_income - cogs
    return {
        "date_from": date_from, "date_to": date_to,
        "income": income, "expenses": expenses,
        "total_income": total_income, "cogs": cogs, "gross_profit": gross_profit,
        "gross_margin_pct": (gross_profit / total_income * 100) if total_income else ZERO,
        "operating_expenses": total_expenses - cogs,
        "total_expenses": total_expenses, "net_profit": total_income - total_expenses,
    }


def vat_return(date_from, date_to):
    """Oman VAT (5%) return summary for a period."""
    output_vat = account_balance(chart.VAT_OUTPUT, date_from, date_to)
    input_vat = account_balance(chart.VAT_INPUT, date_from, date_to)
    taxable_sales = account_balance(chart.SALES, date_from, date_to) + account_balance(
        chart.SALES_RETURNS, date_from, date_to)
    from purchasing.models import SupplierBill

    purchases = SupplierBill.objects.filter(bill_date__range=(date_from, date_to)).exclude(
        status=SupplierBill.Status.CANCELLED).aggregate(t=Sum("subtotal"))["t"] or ZERO
    expenses = Expense.objects.filter(expense_date__range=(date_from, date_to)).aggregate(t=Sum("amount"))["t"] or ZERO
    return {
        "date_from": date_from, "date_to": date_to, "rate": Decimal("5.00"),
        "taxable_sales": taxable_sales, "output_vat": output_vat,
        "taxable_purchases": purchases + expenses, "input_vat": input_vat,
        "net_vat_payable": output_vat - input_vat,
    }


AGING_BUCKETS = [("current", "Current"), ("d1_30", "1-30 days"), ("d31_60", "31-60 days"),
                 ("d61_90", "61-90 days"), ("d90_plus", "90+ days")]


def _bucket(days_overdue):
    if days_overdue <= 0:
        return "current"
    if days_overdue <= 30:
        return "d1_30"
    if days_overdue <= 60:
        return "d31_60"
    if days_overdue <= 90:
        return "d61_90"
    return "d90_plus"


def _aging(documents, party_attr, as_of):
    parties = OrderedDict()
    totals = {key: ZERO for key, _ in AGING_BUCKETS}
    totals["total"] = ZERO
    for doc in documents:
        outstanding = doc.balance_due
        if outstanding <= 0:
            continue
        party = getattr(doc, party_attr)
        row = parties.setdefault(party.pk, {"party": party, **{k: ZERO for k, _ in AGING_BUCKETS}, "total": ZERO,
                                             "documents": []})
        key = _bucket((as_of - doc.due_date).days)
        row[key] += outstanding
        row["total"] += outstanding
        row["documents"].append(doc)
        totals[key] += outstanding
        totals["total"] += outstanding
    rows = sorted(parties.values(), key=lambda r: r["total"], reverse=True)
    return {"rows": rows, "totals": totals, "buckets": AGING_BUCKETS, "as_of": as_of}


def ar_aging(as_of=None):
    """Accounts receivable aging by customer from open sales invoices."""
    from sales.models import Invoice

    as_of = as_of or timezone.localdate()
    invoices = (Invoice.objects.filter(invoice_date__lte=as_of)
                .exclude(status__in=[Invoice.Status.CANCELLED, Invoice.Status.PAID])
                .select_related("customer").order_by("due_date"))
    return _aging(invoices, "customer", as_of)


def ap_aging(as_of=None):
    """Accounts payable aging by supplier from open supplier bills."""
    from purchasing.models import SupplierBill

    as_of = as_of or timezone.localdate()
    bills = (SupplierBill.objects.filter(bill_date__lte=as_of)
             .exclude(status__in=[SupplierBill.Status.CANCELLED, SupplierBill.Status.PAID])
             .select_related("supplier").order_by("due_date"))
    return _aging(bills, "supplier", as_of)


def cash_flow_summary(date_from, date_to):
    """Cash in vs cash out across cash and bank accounts."""
    totals = JournalLine.objects.filter(_line_filter(date_from, date_to), account__code__in=[chart.CASH, chart.BANK]
                                        ).aggregate(d=Sum("debit"), c=Sum("credit"))
    cash_in, cash_out = totals["d"] or ZERO, totals["c"] or ZERO
    return {"cash_in": cash_in, "cash_out": cash_out, "net": cash_in - cash_out}


def month_bounds(day=None):
    day = day or timezone.localdate()
    start = day.replace(day=1)
    next_month = (start + datetime.timedelta(days=32)).replace(day=1)
    return start, next_month - datetime.timedelta(days=1)

