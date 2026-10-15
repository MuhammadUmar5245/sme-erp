import datetime
import os
from decimal import Decimal

import psycopg
import pytest
from django.db import connection
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from conftest import login_verified
from core.factories import CustomerFactory, ProductFactory, WarehouseFactory
from crm.services import record_feedback
from inventory.services import receive_stock
from reports import builder, services
from reports.models import REPORTING_MODELS
from reports.reporting_sql import VIEWS
from sales import services as sales

pytestmark = pytest.mark.django_db
TODAY = datetime.date.today()


@pytest.fixture
def sales_data():
    wh = WarehouseFactory(code="MCT", name="Muscat main")
    tea = ProductFactory(sku="TEA", name="Karak tea", cost_price=Decimal("1.000"), sale_price=Decimal("2.000"),
                         reorder_level=Decimal("5"))
    receive_stock(tea, wh, 50, Decimal("1.000"), update_average_cost=False)
    salalah = CustomerFactory(city="Salalah", name="Dhofar Mart")
    invoice = sales.create_invoice(salalah, wh, [{"product": tea, "quantity": 10}], invoice_date=TODAY)
    sales.create_credit_note(invoice, [{"invoice_line": invoice.lines.get(), "quantity": 2}], "Damaged",
                             credit_date=TODAY)
    sales.record_payment(invoice, Decimal("5.000"), TODAY)
    record_feedback(salalah, 5)
    record_feedback(salalah, 3)
    return {"wh": wh, "tea": tea, "customer": salalah, "invoice": invoice}


def _fetch(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        return cursor.fetchall()


def test_all_views_exist_in_reporting_schema():
    names = {r[0] for r in _fetch("SELECT table_name FROM information_schema.views WHERE table_schema = 'reporting'")}
    assert set(VIEWS) <= names
    assert {"dim_date", "dim_product", "dim_customer", "dim_supplier", "dim_employee", "dim_warehouse", "fact_sales",
            "fact_purchases", "fact_inventory_daily", "fact_payments", "fact_expenses", "fact_feedback"} <= names


def test_dim_date_covers_2024_to_2027_with_oman_calendar():
    assert _fetch("SELECT COUNT(*), MIN(date), MAX(date) FROM reporting.dim_date")[0] == (
        1461, datetime.date(2024, 1, 1), datetime.date(2027, 12, 31))
    friday = _fetch("SELECT is_weekend, day_name FROM reporting.dim_date WHERE date = '2026-10-16'")[0]
    assert friday == (True, "Friday")
    assert _fetch("SELECT is_weekend FROM reporting.dim_date WHERE date = '2026-10-18'")[0][0] is False  # Sunday
    assert _fetch("SELECT is_ramadan FROM reporting.dim_date WHERE date = '2026-03-01'")[0][0] is True
    assert _fetch("SELECT is_khareef FROM reporting.dim_date WHERE date = '2026-08-01'")[0][0] is True


def test_fact_sales_nets_returns(sales_data):
    rows = _fetch("SELECT line_type, quantity, net_amount, cost_amount FROM reporting.fact_sales ORDER BY line_type")
    assert rows == [("RETURN", Decimal("-2.000"), Decimal("-4.000"), Decimal("-2.000")),
                    ("SALE", Decimal("10.000"), Decimal("20.000"), Decimal("10.000"))]
    region = _fetch("SELECT region FROM reporting.dim_customer WHERE customer_id = %s",
                    [sales_data["customer"].pk])[0][0]
    assert region == "Dhofar"


def test_fact_inventory_daily_closing_stock(sales_data):
    closing = _fetch("SELECT closing_qty, is_below_reorder FROM reporting.fact_inventory_daily "
                     "WHERE product_id = %s ORDER BY stock_date DESC LIMIT 1", [sales_data["tea"].pk])[0]
    assert closing == (Decimal("42.000"), False)


def test_fact_payments_and_receivables(sales_data):
    payment = _fetch("SELECT payment_type, amount, cash_flow FROM reporting.fact_payments")[0]
    assert payment == ("CUSTOMER_RECEIPT", Decimal("5.000"), Decimal("5.000"))
    balance = _fetch("SELECT balance_due, aging_bucket FROM reporting.fact_receivables")[0]
    assert balance == (Decimal("11.800"), "Current")


def test_powerbi_reader_is_read_only_on_reporting_schema():
    password = os.environ.get("POWERBI_READER_PASSWORD")
    if not password:
        pytest.skip("POWERBI_READER_PASSWORD not set")
    s = connection.settings_dict
    with psycopg.connect(dbname=s["NAME"], user="powerbi_reader", password=password, host=s["HOST"],
                         port=s["PORT"], autocommit=True) as reader:
        assert reader.execute("SELECT COUNT(*) FROM reporting.dim_date").fetchone()[0] == 1461
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            reader.execute("SELECT * FROM sales_invoice LIMIT 1")
        with pytest.raises(psycopg.Error):
            reader.execute("CREATE TABLE reporting.hack (id int)")


def test_kpis(sales_data):
    k = services.kpis(TODAY)
    assert k["revenue_mtd"] == Decimal("16.000")  # 20 net sales - 4 returned
    assert k["gross_margin_pct"] == Decimal("50.0")
    assert k["outstanding_receivables"] == Decimal("11.800")
    assert k["avg_csat"] == Decimal("4")
    assert k["low_stock_count"] == 0


def test_dashboard_charts(sales_data):
    charts = services.dashboard_charts(TODAY)
    assert charts["sales_by_city"]["labels"] == ["Salalah"]
    assert charts["top_products"]["values"] == [16.0]
    assert charts["monthly_sales"]["sales"][-1] == 16.0
    assert charts["cash_flow"]["cash_in"][-1] == 5.0


def test_reporting_api_requires_permission_and_supports_token(sales_data, make_user):
    viewer = make_user("viewer@alwadi.om", roles=["Viewer"])
    store = make_user("store@alwadi.om", roles=["Storekeeper"])
    client = APIClient()
    assert client.get("/api/v1/reports/fact-sales/").status_code in (401, 403)
    client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=store).key}")
    assert client.get("/api/v1/reports/fact-sales/").status_code == 403
    client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=viewer).key}")
    data = client.get("/api/v1/reports/fact-sales/?page_size=1").json()
    assert data["count"] == 2 and len(data["results"]) == 1 and data["next"]
    yesterday = (TODAY - datetime.timedelta(days=1)).isoformat()
    assert client.get(f"/api/v1/reports/fact-sales/?date_to={yesterday}").json()["count"] == 0
    assert client.get("/api/v1/reports/fact-sales/?date_from=bad").status_code == 400


@pytest.mark.parametrize("slug", list(REPORTING_MODELS))
def test_every_reporting_endpoint_responds(api, admin_user, sales_data, slug):
    response = api(admin_user).get(f"/api/v1/reports/{slug}/?page_size=5")
    assert response.status_code == 200, slug


def test_dataset_index_and_kpi_endpoints(api, admin_user):
    client = api(admin_user)
    assert len(client.get("/api/v1/reports/").json()) == len(REPORTING_MODELS)
    assert "revenue_ytd" in client.get("/api/v1/reports/kpis/").json()


def test_report_builder_groups_and_filters(sales_data):
    report = builder.run_report("sales", ["city", "category"], TODAY.replace(day=1), TODAY, {"city": "Salalah"})
    assert report["headers"][:2] == ["City", "Category"]
    assert report["rows"][0][0] == "Salalah" and report["rows"][0][2] == Decimal("16.000")
    assert builder.run_report("sales", ["city"], TODAY, TODAY, {"city": "Sohar"})["rows"] == []
    snapshot = builder.run_report("inventory", ["product"], TODAY, TODAY)
    assert snapshot["rows"][0][1] == Decimal("42.000")
    for dataset in builder.DATASETS:
        first = next(iter(builder.DATASETS[dataset]["dimensions"]))
        builder.run_report(dataset, [first], TODAY.replace(month=1, day=1), TODAY)


def test_report_builder_rejects_bad_input():
    with pytest.raises(builder.ReportError):
        builder.build_query("sales", ["drop table"], TODAY, TODAY)
    with pytest.raises(builder.ReportError):
        builder.build_query("sales", [], TODAY, TODAY)
    with pytest.raises(builder.ReportError):
        builder.build_query("nope", ["month"], TODAY, TODAY)
    with pytest.raises(builder.ReportError):
        builder.build_query("sales", ["month"], TODAY, TODAY, {"password": "x"})


def test_exports(sales_data):
    report = builder.run_report("sales", ["month"], TODAY.replace(day=1), TODAY)
    assert builder.to_csv(report).decode("utf-8-sig").startswith("Month,Net sales (OMR)")
    assert builder.to_excel(report)[:2] == b"PK"
    assert builder.to_pdf(report)[:4] == b"%PDF"


def test_dashboard_and_builder_pages(client, sales_data, make_user):
    login_verified(client, make_user("mgr@alwadi.om", roles=["Manager"]))
    assert b"Revenue MTD" in client.get(reverse("reports:dashboard")).content
    assert "monthly_sales" in client.get(reverse("reports:dashboard_data")).json()
    page = client.get(reverse("reports:builder") + "?dataset=sales&group_by=city&date_from=2026-01-01")
    assert page.status_code == 200 and b"Salalah" in page.content
    for fmt, ctype in [("csv", "text/csv"), ("xlsx", "spreadsheetml"), ("pdf", "application/pdf")]:
        response = client.get(reverse("reports:export", args=[fmt]) + "?dataset=sales&group_by=month")
        assert response.status_code == 200 and ctype in response["Content-Type"]
    assert b"Revenue YTD" in client.get(reverse("core:dashboard")).content


def test_builder_forbidden_for_storekeeper(client, make_user):
    login_verified(client, make_user("store@alwadi.om", roles=["Storekeeper"]))
    assert client.get(reverse("reports:builder")).status_code == 403
