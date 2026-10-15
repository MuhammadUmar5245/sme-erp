"""REST API tests: permission-checked endpoints and the order-to-cash / procure-to-pay flows over HTTP."""
from decimal import Decimal

import pytest

from core.factories import CustomerFactory, EmployeeFactory, ProductFactory, SupplierFactory, WarehouseFactory
from inventory.services import receive_stock

pytestmark = pytest.mark.django_db


@pytest.fixture
def stock():
    wh = WarehouseFactory()
    product = ProductFactory(sale_price=Decimal("4.000"))
    receive_stock(product, wh, 20, Decimal("2.000"))
    return wh, product


def test_order_to_cash_over_api(api, make_user, stock):
    wh, product = stock
    customer = CustomerFactory()
    client = api(make_user("sales@alwadi.om", roles=["SalesOfficer"]))
    r = client.post("/api/v1/sales/orders/", {"customer": customer.pk, "warehouse": wh.pk,
                                               "input_lines": [{"product": product.pk, "quantity": "5"}]}, format="json")
    assert r.status_code == 201, r.content
    order_id = r.json()["id"]
    assert client.post(f"/api/v1/sales/orders/{order_id}/confirm/").status_code == 200
    r = client.post(f"/api/v1/sales/orders/{order_id}/invoice/")
    assert r.status_code == 201
    invoice = r.json()
    assert invoice["total"] == "21.000"
    r = client.post("/api/v1/sales/payments/", {"invoice": invoice["id"], "amount": "21.000", "method": "CASH"},
                    format="json")
    assert r.status_code == 201
    assert client.get(f"/api/v1/sales/invoices/{invoice['id']}/").json()["status"] == "PAID"


def test_api_invoice_blocked_by_stock(api, admin_user, stock):
    wh, product = stock
    r = api(admin_user).post("/api/v1/sales/invoices/", {
        "customer": CustomerFactory().pk, "warehouse": wh.pk,
        "input_lines": [{"product": product.pk, "quantity": "21"}]}, format="json")
    assert r.status_code == 400 and "Insufficient stock" in r.json()["detail"]


def test_procure_to_pay_over_api(api, make_user, stock):
    wh, product = stock
    supplier = SupplierFactory()
    manager = api(make_user("mgr@alwadi.om", roles=["Manager"]))
    r = manager.post("/api/v1/purchasing/purchase-orders/", {
        "supplier": supplier.pk, "warehouse": wh.pk, "lines": [{"product": product.pk, "quantity": "10"}]},
        format="json")
    assert r.status_code == 201, r.content
    po = r.json()["id"]
    store = api(make_user("store@alwadi.om", roles=["Storekeeper"]))
    assert store.post(f"/api/v1/purchasing/purchase-orders/{po}/approve/").status_code == 403
    assert manager.post(f"/api/v1/purchasing/purchase-orders/{po}/approve/").status_code == 200
    assert store.post(f"/api/v1/purchasing/purchase-orders/{po}/receive/", {}, format="json").status_code == 201
    accountant = api(make_user("acc@alwadi.om", roles=["Accountant"]))
    r = accountant.post(f"/api/v1/purchasing/purchase-orders/{po}/bill/", {"supplier_invoice_no": "INV-9"},
                        format="json")
    assert r.status_code == 201
    r = accountant.post("/api/v1/purchasing/supplier-payments/", {"bill": r.json()["id"], "amount": "5.000"},
                        format="json")
    assert r.status_code == 201


@pytest.mark.parametrize("role,method,url,expected", [
    ("Viewer", "get", "/api/v1/inventory/products/", 200),
    ("Viewer", "post", "/api/v1/inventory/products/", 403),
    ("SalesOfficer", "get", "/api/v1/finance/journal-entries/", 403),
    ("Accountant", "get", "/api/v1/finance/journal-entries/", 200),
    ("Storekeeper", "get", "/api/v1/hr/employees/", 403),
    ("HROfficer", "get", "/api/v1/hr/employees/", 200),
    ("Viewer", "get", "/api/v1/finance/reports/trial-balance/", 200),
    ("Storekeeper", "get", "/api/v1/finance/reports/vat-return/", 403),
])
def test_api_rbac(api, make_user, role, method, url, expected):
    client = api(make_user(f"{role.lower()}@alwadi.om", roles=[role]))
    response = getattr(client, method)(url, {}, format="json") if method == "post" else client.get(url)
    assert response.status_code == expected


@pytest.mark.parametrize("name", ["trial-balance", "profit-loss", "vat-return", "ar-aging", "ap-aging"])
def test_financial_report_endpoints(api, admin_user, name):
    r = api(admin_user).get(f"/api/v1/finance/reports/{name}/?date_from=2026-01-01&date_to=2026-12-31")
    assert r.status_code == 200


def test_unknown_report_404(api, admin_user):
    assert api(admin_user).get("/api/v1/finance/reports/nope/").status_code == 404


def test_stock_movement_api_and_low_stock(api, admin_user, stock):
    wh, product = stock
    client = api(admin_user)
    r = client.post("/api/v1/inventory/stock-movements/", {
        "product": product.pk, "warehouse": wh.pk, "movement_type": "OUT", "quantity": "50"}, format="json")
    assert r.status_code == 400
    r = client.post("/api/v1/inventory/stock-movements/", {
        "product": product.pk, "warehouse": wh.pk, "movement_type": "ADJUST", "quantity": "-2", "note": "count"},
        format="json")
    assert r.status_code == 201
    assert client.get("/api/v1/inventory/products/low-stock/").status_code == 200
    assert client.get("/api/v1/inventory/stock-movements/stock-levels/").status_code == 200


def test_employee_api_masks_sensitive_fields(api, admin_user):
    employee = EmployeeFactory(national_id="99887766")
    data = api(admin_user).get(f"/api/v1/hr/employees/{employee.pk}/").json()
    assert "national_id" not in data and data["national_id_masked"].endswith("7766")


def test_customer_360_api_and_journal_api(api, admin_user, stock):
    client = api(admin_user)
    customer = CustomerFactory()
    assert client.get(f"/api/v1/crm/customers/{customer.pk}/360/").status_code == 200
    from finance.models import Account

    bank, capital = Account.objects.get(code="1010").pk, Account.objects.get(code="3000").pk
    bad = client.post("/api/v1/finance/journal-entries/", {"entry_date": "2026-01-01", "description": "x", "lines": [
        {"account": bank, "debit": "10", "credit": "0"}, {"account": capital, "debit": "0", "credit": "9"}]},
        format="json")
    assert bad.status_code == 400
    good = client.post("/api/v1/finance/journal-entries/", {"entry_date": "2026-01-01", "description": "x", "lines": [
        {"account": bank, "debit": "10", "credit": "0"}, {"account": capital, "debit": "0", "credit": "10"}]},
        format="json")
    assert good.status_code == 201


def test_openapi_schema_generates(client):
    assert client.get("/api/schema/").status_code == 200
