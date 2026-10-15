"""Custom report builder over the reporting views.

Users pick a dataset, a date range, one or more group-by dimensions and optional filters. SQL is
assembled only from the whitelisted fragments below; user values are always bound parameters.
"""
import csv
import datetime
import io
from decimal import Decimal

from django.db import connection

MAX_ROWS = 50000

DATASETS = {
    "sales": {
        "label": "Sales (invoice lines, net of returns)",
        "from": "reporting.fact_sales f JOIN reporting.dim_product p ON p.product_id = f.product_id "
                "JOIN reporting.dim_customer c ON c.customer_id = f.customer_id "
                "JOIN reporting.dim_warehouse w ON w.warehouse_id = f.warehouse_id",
        "date": "f.sales_date",
        "dimensions": {
            "month": ("Month", "to_char(f.sales_date, 'YYYY-MM')"),
            "quarter": ("Quarter", "to_char(f.sales_date, 'YYYY-\"Q\"Q')"),
            "category": ("Category", "p.category_name"),
            "product": ("Product", "p.product_name"),
            "customer": ("Customer", "c.customer_name"),
            "customer_type": ("Customer type", "c.customer_type"),
            "city": ("City", "c.city"),
            "region": ("Region", "c.region"),
            "warehouse": ("Warehouse", "w.warehouse_name"),
            "source": ("Channel", "f.source"),
        },
        "measures": [
            ("Net sales (OMR)", "SUM(f.net_amount)"),
            ("VAT (OMR)", "SUM(f.vat_amount)"),
            ("Gross margin (OMR)", "SUM(f.gross_margin)"),
            ("Margin %", "ROUND(100 * SUM(f.gross_margin) / NULLIF(SUM(f.net_amount), 0), 1)"),
            ("Quantity", "SUM(f.quantity)"),
            ("Invoices", "COUNT(DISTINCT f.invoice_id)"),
        ],
        "filters": {"city": "c.city", "category": "p.category_name", "customer_type": "c.customer_type",
                    "warehouse": "w.warehouse_name"},
    },
    "purchases": {
        "label": "Purchases (PO lines)",
        "from": "reporting.fact_purchases f JOIN reporting.dim_product p ON p.product_id = f.product_id "
                "JOIN reporting.dim_supplier s ON s.supplier_id = f.supplier_id",
        "date": "f.order_date",
        "dimensions": {
            "month": ("Month", "to_char(f.order_date, 'YYYY-MM')"),
            "supplier": ("Supplier", "s.supplier_name"),
            "category": ("Category", "p.category_name"),
            "product": ("Product", "p.product_name"),
            "status": ("Status", "f.status"),
        },
        "measures": [
            ("Net amount (OMR)", "SUM(f.net_amount)"),
            ("VAT (OMR)", "SUM(f.vat_amount)"),
            ("Ordered qty", "SUM(f.quantity)"),
            ("Received qty", "SUM(f.received_quantity)"),
            ("Orders", "COUNT(DISTINCT f.purchase_order_id)"),
        ],
        "filters": {"supplier": "s.supplier_name", "category": "p.category_name", "status": "f.status"},
    },
    "inventory": {
        "label": "Inventory position (closing stock on the end date)",
        "from": "reporting.fact_inventory_daily f JOIN reporting.dim_product p ON p.product_id = f.product_id "
                "JOIN reporting.dim_warehouse w ON w.warehouse_id = f.warehouse_id",
        "date": "f.stock_date",
        "snapshot": True,
        "dimensions": {
            "category": ("Category", "p.category_name"),
            "product": ("Product", "p.product_name"),
            "warehouse": ("Warehouse", "w.warehouse_name"),
        },
        "measures": [
            ("Closing qty", "SUM(f.closing_qty)"),
            ("Closing value (OMR)", "SUM(f.closing_value)"),
            ("Stock-outs", "SUM(CASE WHEN f.is_stockout THEN 1 ELSE 0 END)"),
            ("Below reorder", "SUM(CASE WHEN f.is_below_reorder THEN 1 ELSE 0 END)"),
        ],
        "filters": {"category": "p.category_name", "warehouse": "w.warehouse_name"},
    },
    "payments": {
        "label": "Payments (customer receipts and supplier payments)",
        "from": "reporting.fact_payments f LEFT JOIN reporting.dim_customer c ON c.customer_id = f.customer_id "
                "LEFT JOIN reporting.dim_supplier s ON s.supplier_id = f.supplier_id",
        "date": "f.payment_date",
        "dimensions": {
            "month": ("Month", "to_char(f.payment_date, 'YYYY-MM')"),
            "type": ("Type", "f.payment_type"),
            "method": ("Method", "f.method"),
            "party": ("Customer / supplier", "COALESCE(c.customer_name, s.supplier_name)"),
        },
        "measures": [
            ("Amount (OMR)", "SUM(f.amount)"),
            ("Net cash flow (OMR)", "SUM(f.cash_flow)"),
            ("Payments", "COUNT(*)"),
            ("Avg days to pay", "ROUND(AVG(f.days_to_pay), 1)"),
            ("Avg days late", "ROUND(AVG(GREATEST(f.days_late, 0)), 1)"),
        ],
        "filters": {"type": "f.payment_type", "method": "f.method"},
    },
    "expenses": {
        "label": "Operating expenses",
        "from": "reporting.fact_expenses f",
        "date": "f.expense_date",
        "dimensions": {
            "month": ("Month", "to_char(f.expense_date, 'YYYY-MM')"),
            "category": ("Expense category", "f.expense_category"),
            "payee": ("Payee", "f.payee"),
        },
        "measures": [
            ("Net (OMR)", "SUM(f.amount)"),
            ("VAT (OMR)", "SUM(f.vat_amount)"),
            ("Total (OMR)", "SUM(f.total)"),
            ("Entries", "COUNT(*)"),
        ],
        "filters": {"category": "f.expense_category"},
    },
    "feedback": {
        "label": "Customer satisfaction (CSAT)",
        "from": "reporting.fact_feedback f JOIN reporting.dim_customer c ON c.customer_id = f.customer_id",
        "date": "f.feedback_date",
        "dimensions": {
            "month": ("Month", "to_char(f.feedback_date, 'YYYY-MM')"),
            "city": ("City", "c.city"),
            "customer_type": ("Customer type", "c.customer_type"),
            "channel": ("Channel", "f.channel"),
            "customer": ("Customer", "c.customer_name"),
        },
        "measures": [
            ("Avg CSAT", "ROUND(AVG(f.score), 2)"),
            ("Responses", "COUNT(*)"),
            ("Satisfied %", "ROUND(100.0 * SUM(CASE WHEN f.is_satisfied THEN 1 ELSE 0 END) / COUNT(*), 1)"),
            ("Dissatisfied %", "ROUND(100.0 * SUM(CASE WHEN f.is_dissatisfied THEN 1 ELSE 0 END) / COUNT(*), 1)"),
        ],
        "filters": {"city": "c.city", "channel": "f.channel", "customer_type": "c.customer_type"},
    },
}


class ReportError(ValueError):
    pass


def build_query(dataset, group_by, date_from, date_to, filters=None):
    spec = DATASETS.get(dataset)
    if spec is None:
        raise ReportError("Unknown dataset.")
    group_by = [g for g in group_by if g]
    if not group_by:
        raise ReportError("Choose at least one group-by dimension.")
    unknown = [g for g in group_by if g not in spec["dimensions"]]
    if unknown:
        raise ReportError(f"Invalid group-by: {', '.join(unknown)}")
    select = [f"{spec['dimensions'][g][1]} AS d{i}" for i, g in enumerate(group_by)]
    select += [f"{expr} AS m{i}" for i, (_, expr) in enumerate(spec["measures"])]
    where, params = [], []
    if spec.get("snapshot"):
        where.append(f"{spec['date']} = %s")
        params.append(date_to)
    else:
        where.append(f"{spec['date']} BETWEEN %s AND %s")
        params += [date_from, date_to]
    for key, value in (filters or {}).items():
        if value in (None, ""):
            continue
        if key not in spec["filters"]:
            raise ReportError(f"Invalid filter: {key}")
        where.append(f"{spec['filters'][key]} = %s")
        params.append(value)
    positions = ", ".join(str(i + 1) for i in range(len(group_by)))
    sql = (f"SELECT {', '.join(select)} FROM {spec['from']} WHERE {' AND '.join(where)} "
           f"GROUP BY {positions} ORDER BY {positions} LIMIT {MAX_ROWS}")
    headers = [spec["dimensions"][g][0] for g in group_by] + [label for label, _ in spec["measures"]]
    return sql, params, headers


def run_report(dataset, group_by, date_from, date_to, filters=None):
    sql, params, headers = build_query(dataset, group_by, date_from, date_to, filters)
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
    return {"headers": headers, "rows": rows, "dimension_count": len([g for g in group_by if g]),
            "title": DATASETS[dataset]["label"], "date_from": date_from, "date_to": date_to}


def filter_options(dataset, limit=200):
    """Distinct values for each filter of a dataset (populates the filter dropdowns)."""
    spec = DATASETS[dataset]
    options = {}
    with connection.cursor() as cursor:
        for key, expr in spec["filters"].items():
            cursor.execute(f"SELECT DISTINCT {expr} FROM {spec['from']} WHERE {expr} IS NOT NULL "
                           f"ORDER BY 1 LIMIT {int(limit)}")
            options[key] = [row[0] for row in cursor.fetchall()]
    return options


# ---- Exports ---------------------------------------------------------------------------------


def _cell(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return value


def to_csv(report):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(report["headers"])
    for row in report["rows"]:
        writer.writerow([_cell(v) for v in row])
    return buffer.getvalue().encode("utf-8-sig")


def to_excel(report):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "Report"
    ws.append([f"{report['title']} - {report['date_from']} to {report['date_to']}"])
    ws["A1"].font = Font(bold=True, size=12)
    ws.append([])
    ws.append(report["headers"])
    for cell in ws[3]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="0F4C5C")
    for row in report["rows"]:
        ws.append([_cell(v) for v in row])
    for col in ws.columns:
        width = max(len(str(c.value)) if c.value is not None else 0 for c in col[2:]) if len(col) > 2 else 10
        ws.column_dimensions[col[0].column_letter].width = min(max(width + 2, 10), 45)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def to_pdf(report, company_name="Al Wadi Trading & Distribution LLC"):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=24, rightMargin=24, topMargin=24,
                            bottomMargin=24, title=report["title"])
    styles = getSampleStyleSheet()
    story = [
        Paragraph(company_name, styles["Title"]),
        Paragraph(f"{report['title']} &middot; {report['date_from']} to {report['date_to']}", styles["Heading2"]),
        Paragraph(f"Generated {datetime.datetime.now():%d %b %Y %H:%M} by SME-ERP", styles["Normal"]),
        Spacer(1, 10),
    ]
    data = [report["headers"]]
    for row in report["rows"][:2000]:
        data.append([f"{v:,.3f}" if isinstance(v, Decimal) else ("" if v is None else str(v)) for v in row])
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F4C5C")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F8")]),
        ("ALIGN", (report["dimension_count"], 1), (-1, -1), "RIGHT"),
    ]))
    story.append(table)
    if len(report["rows"]) > 2000:
        story.append(Paragraph(f"Showing the first 2,000 of {len(report['rows'])} rows; use Excel or CSV for all rows.",
                               styles["Italic"]))
    doc.build(story)
    return buffer.getvalue()
