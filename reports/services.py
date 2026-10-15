"""Analytics: KPI cards and chart series for the in-app dashboard (also served at /api/v1/reports/kpis/)."""
import datetime
from decimal import Decimal

from django.db import connection
from django.db.models import Avg, DecimalField, F, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from crm.models import Feedback
from finance import chart
from finance.models import JournalLine
from inventory.services import inventory_value, low_stock_products
from sales.models import CreditNote, Invoice

ZERO = Decimal("0")


def _sum(qs, field):
    return qs.aggregate(t=Coalesce(Sum(field), ZERO, output_field=DecimalField(max_digits=16, decimal_places=3)))["t"]


def net_sales(date_from, date_to):
    """Invoiced net sales less credit notes for a period."""
    invoices = Invoice.objects.exclude(status=Invoice.Status.CANCELLED).filter(invoice_date__range=(date_from, date_to))
    credits = CreditNote.objects.filter(credit_date__range=(date_from, date_to))
    return _sum(invoices, "subtotal") - _sum(credits, "subtotal")


def gross_margin_pct(date_from, date_to):
    invoices = Invoice.objects.exclude(status=Invoice.Status.CANCELLED).filter(invoice_date__range=(date_from, date_to))
    credits = CreditNote.objects.filter(credit_date__range=(date_from, date_to))
    revenue = _sum(invoices, "subtotal") - _sum(credits, "subtotal")
    cost = _sum(invoices, "cost_total") - _sum(credits, "cost_total")
    if not revenue:
        return ZERO
    return ((revenue - cost) / revenue * 100).quantize(Decimal("0.1"))


def outstanding_receivables(as_of=None):
    open_invoices = Invoice.objects.exclude(status__in=[Invoice.Status.CANCELLED, Invoice.Status.PAID])
    total = _sum(open_invoices.annotate(bal=F("total") - F("amount_paid") - F("amount_credited")), "bal")
    overdue = _sum(open_invoices.filter(due_date__lt=as_of or timezone.localdate())
                   .annotate(bal=F("total") - F("amount_paid") - F("amount_credited")), "bal")
    return total, overdue


def average_csat(days=365, as_of=None):
    as_of = as_of or timezone.localdate()
    value = Feedback.objects.filter(feedback_date__gt=as_of - datetime.timedelta(days=days)).aggregate(
        a=Avg("score"))["a"]
    return Decimal(str(round(value, 2))) if value is not None else None


def kpis(today=None):
    today = today or timezone.localdate()
    month_start, year_start = today.replace(day=1), today.replace(month=1, day=1)
    receivables, overdue = outstanding_receivables(today)
    return {
        "revenue_mtd": net_sales(month_start, today),
        "revenue_ytd": net_sales(year_start, today),
        "gross_margin_pct": gross_margin_pct(year_start, today),
        "outstanding_receivables": receivables,
        "overdue_receivables": overdue,
        "low_stock_count": len(low_stock_products()),
        "avg_csat": average_csat(as_of=today),
        "inventory_value": inventory_value(),
        "as_of": today,
    }


def _rows(sql, params):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def monthly_sales(months=18, today=None):
    today = today or timezone.localdate()
    start = (today.replace(day=1) - datetime.timedelta(days=31 * (months - 1))).replace(day=1)
    rows = {
        month: (amount, margin_amount)
        for month, amount, margin_amount in _rows(
            "SELECT to_char(sales_date, 'YYYY-MM'), SUM(net_amount), SUM(gross_margin) FROM reporting.fact_sales "
            "WHERE sales_date BETWEEN %s AND %s GROUP BY 1", [start, today])
    }
    labels, sales, margin = [], [], []
    cursor = start
    while cursor <= today:
        key = cursor.strftime("%Y-%m")
        labels.append(cursor.strftime("%b %Y"))
        value = rows.get(key, (ZERO, ZERO))
        sales.append(float(value[0] or 0))
        margin.append(float(value[1] or 0))
        cursor = (cursor + datetime.timedelta(days=32)).replace(day=1)
    return {"labels": labels, "sales": sales, "margin": margin}


def top_products(limit=10, date_from=None, date_to=None):
    date_to = date_to or timezone.localdate()
    date_from = date_from or date_to - datetime.timedelta(days=365)
    rows = _rows(
        "SELECT p.product_name, SUM(f.net_amount) FROM reporting.fact_sales f "
        "JOIN reporting.dim_product p ON p.product_id = f.product_id WHERE f.sales_date BETWEEN %s AND %s "
        "GROUP BY 1 ORDER BY 2 DESC LIMIT %s", [date_from, date_to, limit])
    return {"labels": [r[0] for r in rows], "values": [float(r[1]) for r in rows]}


def sales_by_city(date_from=None, date_to=None):
    date_to = date_to or timezone.localdate()
    date_from = date_from or date_to - datetime.timedelta(days=365)
    rows = _rows(
        "SELECT c.city, SUM(f.net_amount) FROM reporting.fact_sales f "
        "JOIN reporting.dim_customer c ON c.customer_id = f.customer_id WHERE f.sales_date BETWEEN %s AND %s "
        "GROUP BY 1 ORDER BY 2 DESC", [date_from, date_to])
    return {"labels": [r[0] for r in rows], "values": [float(r[1]) for r in rows]}


def cash_in_out(months=12, today=None):
    today = today or timezone.localdate()
    start = (today.replace(day=1) - datetime.timedelta(days=31 * (months - 1))).replace(day=1)
    rows = (JournalLine.objects.filter(account__code__in=[chart.CASH, chart.BANK], entry__entry_date__range=(start, today))
            .values_list("entry__entry_date__year", "entry__entry_date__month")
            .annotate(cash_in=Sum("debit"), cash_out=Sum("credit")))
    data = {(y, m): (i, o) for y, m, i, o in rows}
    labels, cash_in, cash_out = [], [], []
    cursor = start
    while cursor <= today:
        i, o = data.get((cursor.year, cursor.month), (0, 0))
        labels.append(cursor.strftime("%b %Y"))
        cash_in.append(float(i or 0))
        cash_out.append(float(o or 0))
        cursor = (cursor + datetime.timedelta(days=32)).replace(day=1)
    return {"labels": labels, "cash_in": cash_in, "cash_out": cash_out}


def dashboard_charts(today=None):
    return {
        "monthly_sales": monthly_sales(today=today),
        "top_products": top_products(date_to=today),
        "sales_by_city": sales_by_city(date_to=today),
        "cash_flow": cash_in_out(today=today),
    }
