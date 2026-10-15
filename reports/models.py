"""Read-only models over the PostgreSQL `reporting` schema views (managed=False: no tables are created)."""
from django.db import models


class ReportAccess(models.Model):
    """Holder for reporting permissions (no table)."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = [
            ("view_dashboard", "Can view analytics dashboards and the report builder"),
            ("view_powerbi_api", "Can read the Power BI reporting API"),
        ]


def _money(**kw):
    return models.DecimalField(max_digits=16, decimal_places=3, null=True, **kw)


class ReportingView(models.Model):
    date_field = None  # field used by ?date_from / ?date_to filters

    class Meta:
        abstract = True
        managed = False


class DimDate(ReportingView):
    date_key = models.IntegerField(primary_key=True)
    date = models.DateField()
    year = models.IntegerField()
    quarter = models.IntegerField()
    quarter_label = models.CharField(max_length=2)
    month = models.IntegerField()
    month_name = models.CharField(max_length=12)
    month_short = models.CharField(max_length=3)
    year_month = models.CharField(max_length=7)
    week_of_year = models.IntegerField()
    day_of_month = models.IntegerField()
    day_of_week = models.IntegerField()
    day_name = models.CharField(max_length=10)
    is_weekend = models.BooleanField()
    is_ramadan = models.BooleanField()
    is_eid = models.BooleanField()
    is_summer = models.BooleanField()
    is_khareef = models.BooleanField()
    date_field = "date"

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."dim_date'
        ordering = ["date_key"]


class DimProduct(ReportingView):
    product_id = models.BigIntegerField(primary_key=True)
    sku = models.CharField(max_length=30)
    product_name = models.CharField(max_length=150)
    category_id = models.BigIntegerField()
    category_code = models.CharField(max_length=20)
    category_name = models.CharField(max_length=100)
    unit = models.CharField(max_length=5)
    cost_price = _money()
    sale_price = _money()
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2)
    reorder_level = models.DecimalField(max_digits=12, decimal_places=3)
    reorder_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    is_active = models.BooleanField()

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."dim_product'
        ordering = ["product_id"]


class DimCustomer(ReportingView):
    customer_id = models.BigIntegerField(primary_key=True)
    customer_code = models.CharField(max_length=20)
    customer_name = models.CharField(max_length=150)
    customer_type = models.CharField(max_length=12)
    city = models.CharField(max_length=30)
    region = models.CharField(max_length=30)
    credit_limit = _money()
    payment_terms_days = models.IntegerField()
    is_active = models.BooleanField()
    created_date = models.DateField()

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."dim_customer'
        ordering = ["customer_id"]


class DimSupplier(ReportingView):
    supplier_id = models.BigIntegerField(primary_key=True)
    supplier_code = models.CharField(max_length=20)
    supplier_name = models.CharField(max_length=150)
    city = models.CharField(max_length=50)
    country = models.CharField(max_length=50)
    payment_terms_days = models.IntegerField()
    is_active = models.BooleanField()

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."dim_supplier'
        ordering = ["supplier_id"]


class DimEmployee(ReportingView):
    employee_id = models.BigIntegerField(primary_key=True)
    employee_no = models.CharField(max_length=20)
    full_name = models.CharField(max_length=170)
    department = models.CharField(max_length=100)
    job_title = models.CharField(max_length=100)
    city = models.CharField(max_length=50)
    nationality = models.CharField(max_length=50)
    hire_date = models.DateField()
    is_active = models.BooleanField()
    user_id = models.BigIntegerField(null=True)
    date_field = "hire_date"

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."dim_employee'
        ordering = ["employee_id"]


class DimWarehouse(ReportingView):
    warehouse_id = models.BigIntegerField(primary_key=True)
    warehouse_code = models.CharField(max_length=20)
    warehouse_name = models.CharField(max_length=100)
    city = models.CharField(max_length=50)
    is_active = models.BooleanField()

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."dim_warehouse'
        ordering = ["warehouse_id"]


class FactSales(ReportingView):
    sales_line_id = models.BigIntegerField(primary_key=True)
    line_type = models.CharField(max_length=6)
    invoice_id = models.BigIntegerField()
    document_number = models.CharField(max_length=30)
    date_key = models.IntegerField()
    sales_date = models.DateField()
    customer_id = models.BigIntegerField()
    product_id = models.BigIntegerField()
    warehouse_id = models.BigIntegerField()
    salesperson_id = models.BigIntegerField(null=True)
    source = models.CharField(max_length=6)
    status = models.CharField(max_length=10)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_price = _money()
    discount_pct = models.DecimalField(max_digits=5, decimal_places=2)
    net_amount = _money()
    vat_amount = _money()
    gross_amount = _money()
    cost_amount = _money()
    gross_margin = _money()
    date_field = "sales_date"

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."fact_sales'
        ordering = ["sales_date", "sales_line_id"]


class FactPurchases(ReportingView):
    purchase_line_id = models.BigIntegerField(primary_key=True)
    purchase_order_id = models.BigIntegerField()
    po_number = models.CharField(max_length=30)
    date_key = models.IntegerField()
    order_date = models.DateField()
    supplier_id = models.BigIntegerField()
    product_id = models.BigIntegerField()
    warehouse_id = models.BigIntegerField()
    status = models.CharField(max_length=10)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    received_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost = _money()
    net_amount = _money()
    vat_amount = _money()
    total_amount = _money()
    date_field = "order_date"

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."fact_purchases'
        ordering = ["order_date", "purchase_line_id"]


class FactInventoryDaily(ReportingView):
    row_id = models.BigIntegerField(primary_key=True)
    stock_date = models.DateField()
    date_key = models.IntegerField()
    product_id = models.BigIntegerField()
    warehouse_id = models.BigIntegerField()
    qty_in = models.DecimalField(max_digits=14, decimal_places=3)
    qty_out = models.DecimalField(max_digits=14, decimal_places=3)
    closing_qty = models.DecimalField(max_digits=14, decimal_places=3)
    closing_value = _money()
    reorder_level = models.DecimalField(max_digits=12, decimal_places=3)
    is_stockout = models.BooleanField()
    is_below_reorder = models.BooleanField()
    date_field = "stock_date"

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."fact_inventory_daily'
        ordering = ["stock_date", "row_id"]


class FactPayments(ReportingView):
    payment_row_id = models.BigIntegerField(primary_key=True)
    payment_type = models.CharField(max_length=20)
    payment_number = models.CharField(max_length=30)
    date_key = models.IntegerField()
    payment_date = models.DateField()
    customer_id = models.BigIntegerField(null=True)
    supplier_id = models.BigIntegerField(null=True)
    document_id = models.BigIntegerField()
    document_number = models.CharField(max_length=30)
    method = models.CharField(max_length=6)
    amount = _money()
    cash_flow = _money()
    document_date = models.DateField()
    due_date = models.DateField()
    days_to_pay = models.IntegerField()
    days_late = models.IntegerField()
    date_field = "payment_date"

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."fact_payments'
        ordering = ["payment_date", "payment_row_id"]


class FactExpenses(ReportingView):
    expense_id = models.BigIntegerField(primary_key=True)
    expense_number = models.CharField(max_length=30)
    date_key = models.IntegerField()
    expense_date = models.DateField()
    account_code = models.CharField(max_length=10)
    expense_category = models.CharField(max_length=100)
    payee = models.CharField(max_length=120)
    description = models.CharField(max_length=200)
    amount = _money()
    vat_amount = _money()
    total = _money()
    paid_from = models.CharField(max_length=4)
    date_field = "expense_date"

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."fact_expenses'
        ordering = ["expense_date", "expense_id"]


class FactFeedback(ReportingView):
    feedback_id = models.BigIntegerField(primary_key=True)
    date_key = models.IntegerField()
    feedback_date = models.DateField()
    customer_id = models.BigIntegerField()
    invoice_id = models.BigIntegerField(null=True)
    score = models.IntegerField()
    channel = models.CharField(max_length=10)
    is_satisfied = models.BooleanField()
    is_dissatisfied = models.BooleanField()
    comment = models.TextField()
    date_field = "feedback_date"

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."fact_feedback'
        ordering = ["feedback_date", "feedback_id"]


class FactInteractions(ReportingView):
    interaction_id = models.BigIntegerField(primary_key=True)
    date_key = models.IntegerField()
    interaction_date = models.DateField()
    customer_id = models.BigIntegerField()
    interaction_type = models.CharField(max_length=10)
    status = models.CharField(max_length=6)
    is_complaint = models.BooleanField()
    date_field = "interaction_date"

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."fact_interactions'
        ordering = ["interaction_date", "interaction_id"]


class FactReceivables(ReportingView):
    invoice_id = models.BigIntegerField(primary_key=True)
    invoice_number = models.CharField(max_length=30)
    date_key = models.IntegerField()
    invoice_date = models.DateField()
    due_date = models.DateField()
    customer_id = models.BigIntegerField()
    status = models.CharField(max_length=10)
    total = _money()
    amount_paid = _money()
    amount_credited = _money()
    balance_due = _money()
    days_overdue = models.IntegerField()
    aging_bucket = models.CharField(max_length=10)
    date_field = "invoice_date"

    class Meta(ReportingView.Meta):
        db_table = 'reporting"."fact_receivables'
        ordering = ["invoice_date", "invoice_id"]


# URL slug -> model, used by the Power BI API router and the documentation.
REPORTING_MODELS = {
    "dim-date": DimDate,
    "dim-product": DimProduct,
    "dim-customer": DimCustomer,
    "dim-supplier": DimSupplier,
    "dim-employee": DimEmployee,
    "dim-warehouse": DimWarehouse,
    "fact-sales": FactSales,
    "fact-purchases": FactPurchases,
    "fact-inventory-daily": FactInventoryDaily,
    "fact-payments": FactPayments,
    "fact-expenses": FactExpenses,
    "fact-feedback": FactFeedback,
    "fact-interactions": FactInteractions,
    "fact-receivables": FactReceivables,
}
