"""PostgreSQL `reporting` schema: star-schema views (dim_*, fact_*) for Power BI and the report builder.

The views are (re)built by migrations via `rebuild_views()`. Power BI connects with the read-only
role `powerbi_reader`, which can only SELECT from this schema - never from the operational tables.
"""
from core.oman_calendar import eid_sql_condition, ramadan_sql_condition

SCHEMA = "reporting"
TZ = "Asia/Muscat"

REGION_CASE = """CASE
    WHEN c.city IN ('Muscat', 'Seeb', 'Bawshar') THEN 'Muscat'
    WHEN c.city = 'Sohar' THEN 'North Al Batinah'
    WHEN c.city IN ('Barka', 'Rustaq') THEN 'South Al Batinah'
    WHEN c.city = 'Salalah' THEN 'Dhofar'
    WHEN c.city = 'Nizwa' THEN 'Ad Dakhiliyah'
    WHEN c.city = 'Sur' THEN 'South Ash Sharqiyah'
    WHEN c.city = 'Ibri' THEN 'Ad Dhahirah'
    ELSE 'Other' END"""

VIEWS = {
    "dim_date": f"""
        SELECT to_char(d, 'YYYYMMDD')::int AS date_key,
               d::date AS date,
               extract(year FROM d)::int AS year,
               extract(quarter FROM d)::int AS quarter,
               'Q' || extract(quarter FROM d)::int AS quarter_label,
               extract(month FROM d)::int AS month,
               trim(to_char(d, 'Month')) AS month_name,
               to_char(d, 'Mon') AS month_short,
               to_char(d, 'YYYY-MM') AS year_month,
               extract(week FROM d)::int AS week_of_year,
               extract(day FROM d)::int AS day_of_month,
               extract(isodow FROM d)::int AS day_of_week,
               trim(to_char(d, 'Day')) AS day_name,
               extract(isodow FROM d) IN (5, 6) AS is_weekend,
               {ramadan_sql_condition('d::date')} AS is_ramadan,
               {eid_sql_condition('d::date')} AS is_eid,
               (extract(month FROM d) BETWEEN 6 AND 8) AS is_summer,
               (d::date BETWEEN make_date(extract(year FROM d)::int, 6, 21)
                            AND make_date(extract(year FROM d)::int, 9, 21)) AS is_khareef
        FROM generate_series(DATE '2024-01-01', DATE '2027-12-31', interval '1 day') AS d
    """,
    "dim_product": """
        SELECT p.id AS product_id, p.sku, p.name AS product_name, p.category_id, cat.code AS category_code,
               cat.name AS category_name, p.unit, p.cost_price, p.sale_price, p.vat_rate, p.reorder_level,
               p.reorder_quantity, p.is_active
        FROM inventory_product p JOIN inventory_category cat ON cat.id = p.category_id
    """,
    "dim_customer": f"""
        SELECT c.id AS customer_id, c.code AS customer_code, c.name AS customer_name, c.customer_type, c.city,
               {REGION_CASE} AS region, c.credit_limit, c.payment_terms_days, c.is_active,
               (c.created_at AT TIME ZONE '{TZ}')::date AS created_date
        FROM crm_customer c
    """,
    "dim_supplier": """
        SELECT s.id AS supplier_id, s.code AS supplier_code, s.name AS supplier_name, s.city, s.country,
               s.payment_terms_days, s.is_active
        FROM purchasing_supplier s
    """,
    "dim_employee": """
        SELECT e.id AS employee_id, e.employee_no, e.first_name || ' ' || e.last_name AS full_name,
               d.name AS department, e.job_title, e.city, e.nationality, e.hire_date, e.is_active, e.user_id
        FROM hr_employee e JOIN hr_department d ON d.id = e.department_id
    """,
    "dim_warehouse": """
        SELECT w.id AS warehouse_id, w.code AS warehouse_code, w.name AS warehouse_name, w.city, w.is_active
        FROM inventory_warehouse w
    """,
    "fact_sales": """
        SELECT l.id AS sales_line_id, 'SALE' AS line_type, i.id AS invoice_id, i.number AS document_number,
               to_char(i.invoice_date, 'YYYYMMDD')::int AS date_key, i.invoice_date AS sales_date,
               i.customer_id, l.product_id, i.warehouse_id, i.salesperson_id, i.source, i.status,
               l.quantity, l.unit_price, l.discount_pct, l.line_subtotal AS net_amount, l.line_vat AS vat_amount,
               l.line_total AS gross_amount, round(l.quantity * l.unit_cost, 3) AS cost_amount,
               l.line_subtotal - round(l.quantity * l.unit_cost, 3) AS gross_margin
        FROM sales_invoiceline l JOIN sales_invoice i ON i.id = l.invoice_id
        WHERE i.status <> 'CANCELLED'
        UNION ALL
        SELECT -cl.id, 'RETURN', i.id, cn.number, to_char(cn.credit_date, 'YYYYMMDD')::int, cn.credit_date,
               cn.customer_id, cl.product_id, i.warehouse_id, i.salesperson_id, i.source, i.status,
               -cl.quantity, cl.unit_price, 0, -cl.line_subtotal, -cl.line_vat, -cl.line_total,
               CASE WHEN cn.restock THEN -round(cl.quantity * cl.unit_cost, 3) ELSE 0 END,
               -cl.line_subtotal - CASE WHEN cn.restock THEN -round(cl.quantity * cl.unit_cost, 3) ELSE 0 END
        FROM sales_creditnoteline cl JOIN sales_creditnote cn ON cn.id = cl.credit_note_id
             JOIN sales_invoice i ON i.id = cn.invoice_id
    """,
    "fact_purchases": """
        SELECT l.id AS purchase_line_id, o.id AS purchase_order_id, o.number AS po_number,
               to_char(o.order_date, 'YYYYMMDD')::int AS date_key, o.order_date, o.supplier_id, l.product_id,
               o.warehouse_id, o.status, l.quantity, l.received_quantity, l.unit_cost,
               round(l.quantity * l.unit_cost, 3) AS net_amount,
               round(round(l.quantity * l.unit_cost, 3) * l.vat_rate / 100, 3) AS vat_amount,
               round(l.quantity * l.unit_cost, 3) + round(round(l.quantity * l.unit_cost, 3) * l.vat_rate / 100, 3)
                   AS total_amount
        FROM purchasing_purchaseorderline l JOIN purchasing_purchaseorder o ON o.id = l.order_id
        WHERE o.status <> 'CANCELLED'
    """,
    "fact_inventory_daily": f"""
        WITH daily AS (
            SELECT product_id, warehouse_id, (movement_date AT TIME ZONE '{TZ}')::date AS d,
                   SUM(quantity) AS net_qty,
                   SUM(CASE WHEN quantity > 0 THEN quantity ELSE 0 END) AS qty_in,
                   SUM(CASE WHEN quantity < 0 THEN -quantity ELSE 0 END) AS qty_out
            FROM inventory_stockmovement GROUP BY 1, 2, 3
        ), pairs AS (
            SELECT product_id, warehouse_id, MIN(d) AS first_day FROM daily GROUP BY 1, 2
        ), calendar AS (
            SELECT p.product_id, p.warehouse_id, gs::date AS d
            FROM pairs p CROSS JOIN LATERAL generate_series(
                p.first_day, (now() AT TIME ZONE '{TZ}')::date, interval '1 day') AS gs
        ), running AS (
            SELECT c.product_id, c.warehouse_id, c.d,
                   COALESCE(dl.qty_in, 0) AS qty_in, COALESCE(dl.qty_out, 0) AS qty_out,
                   SUM(COALESCE(dl.net_qty, 0)) OVER (PARTITION BY c.product_id, c.warehouse_id ORDER BY c.d)
                       AS closing_qty
            FROM calendar c LEFT JOIN daily dl
                 ON dl.product_id = c.product_id AND dl.warehouse_id = c.warehouse_id AND dl.d = c.d
        )
        SELECT (r.product_id * 1000 + r.warehouse_id) * 100000 + (r.d - DATE '2020-01-01') AS row_id,
               r.d AS stock_date, to_char(r.d, 'YYYYMMDD')::int AS date_key, r.product_id, r.warehouse_id,
               r.qty_in, r.qty_out, r.closing_qty, round(r.closing_qty * p.cost_price, 3) AS closing_value,
               p.reorder_level, r.closing_qty <= 0 AS is_stockout, r.closing_qty <= p.reorder_level AS is_below_reorder
        FROM running r JOIN inventory_product p ON p.id = r.product_id
    """,
    "fact_payments": """
        SELECT p.id AS payment_row_id, 'CUSTOMER_RECEIPT' AS payment_type, p.number AS payment_number,
               to_char(p.payment_date, 'YYYYMMDD')::int AS date_key, p.payment_date, p.customer_id,
               NULL::bigint AS supplier_id, p.invoice_id AS document_id, i.number AS document_number, p.method,
               p.amount, p.amount AS cash_flow, i.invoice_date AS document_date, i.due_date,
               (p.payment_date - i.invoice_date) AS days_to_pay, (p.payment_date - i.due_date) AS days_late
        FROM sales_payment p JOIN sales_invoice i ON i.id = p.invoice_id
        UNION ALL
        SELECT -sp.id, 'SUPPLIER_PAYMENT', sp.number, to_char(sp.payment_date, 'YYYYMMDD')::int, sp.payment_date,
               NULL, sp.supplier_id, sp.bill_id, b.number, sp.method, sp.amount, -sp.amount, b.bill_date,
               b.due_date, (sp.payment_date - b.bill_date), (sp.payment_date - b.due_date)
        FROM purchasing_supplierpayment sp JOIN purchasing_supplierbill b ON b.id = sp.bill_id
    """,
    "fact_expenses": """
        SELECT e.id AS expense_id, e.number AS expense_number, to_char(e.expense_date, 'YYYYMMDD')::int AS date_key,
               e.expense_date, a.code AS account_code, a.name AS expense_category, e.payee, e.description,
               e.amount, e.vat_amount, e.total, e.paid_from
        FROM finance_expense e JOIN finance_account a ON a.id = e.account_id
    """,
    "fact_feedback": """
        SELECT f.id AS feedback_id, to_char(f.feedback_date, 'YYYYMMDD')::int AS date_key, f.feedback_date,
               f.customer_id, f.invoice_id, f.score, f.channel, f.score >= 4 AS is_satisfied,
               f.score <= 2 AS is_dissatisfied, f.comment
        FROM crm_feedback f
    """,
    "fact_interactions": f"""
        SELECT x.id AS interaction_id, to_char((x.interaction_date AT TIME ZONE '{TZ}')::date, 'YYYYMMDD')::int
                   AS date_key,
               (x.interaction_date AT TIME ZONE '{TZ}')::date AS interaction_date, x.customer_id,
               x.interaction_type, x.status, x.interaction_type = 'COMPLAINT' AS is_complaint
        FROM crm_interaction x
    """,
    "fact_receivables": f"""
        SELECT i.id AS invoice_id, i.number AS invoice_number, to_char(i.invoice_date, 'YYYYMMDD')::int AS date_key,
               i.invoice_date, i.due_date, i.customer_id, i.status, i.total, i.amount_paid, i.amount_credited,
               i.total - i.amount_paid - i.amount_credited AS balance_due,
               GREATEST((now() AT TIME ZONE '{TZ}')::date - i.due_date, 0) AS days_overdue,
               CASE WHEN i.total - i.amount_paid - i.amount_credited <= 0 THEN 'Settled'
                    WHEN (now() AT TIME ZONE '{TZ}')::date <= i.due_date THEN 'Current'
                    WHEN (now() AT TIME ZONE '{TZ}')::date - i.due_date <= 30 THEN '1-30'
                    WHEN (now() AT TIME ZONE '{TZ}')::date - i.due_date <= 60 THEN '31-60'
                    WHEN (now() AT TIME ZONE '{TZ}')::date - i.due_date <= 90 THEN '61-90'
                    ELSE '90+' END AS aging_bucket
        FROM sales_invoice i WHERE i.status <> 'CANCELLED'
    """,
}


def rebuild_views(cursor):
    """Drop and recreate the reporting schema with every view (idempotent)."""
    cursor.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    cursor.execute(f"CREATE SCHEMA {SCHEMA}")
    cursor.execute(f"COMMENT ON SCHEMA {SCHEMA} IS 'Read-only star schema for Power BI (dim_*, fact_*)'")
    for name, sql in VIEWS.items():
        cursor.execute(f"CREATE VIEW {SCHEMA}.{name} AS {sql}")
    grant_reader(cursor)


def grant_reader(cursor, role="powerbi_reader"):
    """(Re)apply the read-only grants if the role exists."""
    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [role])
    if cursor.fetchone():
        cursor.execute(f"GRANT USAGE ON SCHEMA {SCHEMA} TO {role}")
        cursor.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA {SCHEMA} TO {role}")
        cursor.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {SCHEMA} GRANT SELECT ON TABLES TO {role}")


def create_powerbi_reader(cursor, password, role="powerbi_reader"):
    """Create/update the LOGIN role used only by Power BI: SELECT on schema reporting, nothing else."""
    if not password:
        return False
    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [role])
    exists = cursor.fetchone()
    verb = "ALTER" if exists else "CREATE"
    # Identifiers are constants; the password is passed as a quoted literal.
    cursor.execute(
        f"{verb} ROLE {role} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT "
        f"CONNECTION LIMIT 20 PASSWORD %s", [password]
    )
    cursor.execute("SELECT current_database()")
    database = cursor.fetchone()[0]
    cursor.execute(f'GRANT CONNECT ON DATABASE "{database}" TO {role}')
    cursor.execute(f"REVOKE ALL ON SCHEMA public FROM {role}")
    cursor.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {role}")
    cursor.execute(f"ALTER ROLE {role} SET default_transaction_read_only = on")
    cursor.execute(f"ALTER ROLE {role} SET statement_timeout = '120s'")
    grant_reader(cursor, role)
    return True
