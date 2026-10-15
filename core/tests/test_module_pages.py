"""UI smoke + RBAC tests across the business modules (list/detail/create/edit pages, search, filters)."""
import datetime
from decimal import Decimal

import pytest
from django.urls import reverse

from conftest import login_verified
from core.factories import CustomerFactory, EmployeeFactory, ProductFactory, SupplierFactory, WarehouseFactory
from crm.models import Interaction
from crm.services import log_interaction, record_feedback
from finance.services import record_expense
from hr.services import submit_leave_request
from inventory.services import receive_stock
from purchasing import services as purchasing
from sales import services as sales

pytestmark = pytest.mark.django_db


@pytest.fixture
def data():
    wh = WarehouseFactory(code="MCT", name="Muscat main")
    product = ProductFactory(sku="TEA-01", name="Karak tea 100 bags", sale_price=Decimal("2.000"))
    receive_stock(product, wh, 100, Decimal("1.000"))
    customer = CustomerFactory(name="Al Fair Supermarket")
    supplier = SupplierFactory(name="Gulf Foods LLC")
    order = sales.create_sales_order(customer, wh, [{"product": product, "quantity": 2}])
    invoice = sales.create_invoice(customer, wh, [{"product": product, "quantity": 3}])
    sales.record_payment(invoice, Decimal("1.000"))
    note = sales.create_credit_note(invoice, [{"invoice_line": invoice.lines.first(), "quantity": 1}], "Damaged")
    po = purchasing.create_purchase_order(supplier, wh, [{"product": product, "quantity": 10}])
    purchasing.approve_purchase_order(po)
    grn = purchasing.receive_goods(po)
    bill = purchasing.create_bill_from_po(po, "GF-1")
    interaction = log_interaction(customer, Interaction.Type.COMPLAINT, "Late delivery")
    record_feedback(customer, 4)
    expense = record_expense(datetime.date.today(), "6300", "Shell", "Fuel", 20)
    employee = EmployeeFactory()
    leave = submit_leave_request(employee, "SICK", datetime.date(2026, 3, 1), datetime.date(2026, 3, 1))
    return locals()


def _pages(d):
    from finance.models import Account, JournalEntry

    journal = JournalEntry.objects.first()
    return [
        reverse("inventory:product_list"), reverse("inventory:product_list") + "?q=tea&is_active=true",
        reverse("inventory:product_detail", args=[d["product"].pk]), reverse("inventory:product_create"),
        reverse("inventory:product_update", args=[d["product"].pk]),
        reverse("inventory:category_list"), reverse("inventory:warehouse_list"),
        reverse("inventory:warehouse_detail", args=[d["wh"].pk]), reverse("inventory:stock_levels"),
        reverse("inventory:stock_levels") + "?low=1", reverse("inventory:movement_list"),
        reverse("inventory:stock_operation"),
        reverse("purchasing:supplier_list"), reverse("purchasing:supplier_detail", args=[d["supplier"].pk]),
        reverse("purchasing:po_list"), reverse("purchasing:po_detail", args=[d["po"].pk]),
        reverse("purchasing:po_create"), reverse("purchasing:grn_list"),
        reverse("purchasing:grn_detail", args=[d["grn"].pk]), reverse("purchasing:bill_list"),
        reverse("purchasing:bill_detail", args=[d["bill"].pk]), reverse("purchasing:bill_pay", args=[d["bill"].pk]),
        reverse("sales:order_list"), reverse("sales:order_detail", args=[d["order"].pk]),
        reverse("sales:order_create"), reverse("sales:order_update", args=[d["order"].pk]),
        reverse("sales:invoice_list") + "?status=PARTIAL", reverse("sales:invoice_detail", args=[d["invoice"].pk]),
        reverse("sales:invoice_create"), reverse("sales:invoice_print", args=[d["invoice"].pk]),
        reverse("sales:invoice_pay", args=[d["invoice"].pk]), reverse("sales:invoice_credit", args=[d["invoice"].pk]),
        reverse("sales:payment_list"), reverse("sales:creditnote_list"),
        reverse("sales:creditnote_detail", args=[d["note"].pk]),
        reverse("crm:customer_list"), reverse("crm:customer_detail", args=[d["customer"].pk]),
        reverse("crm:customer_create"), reverse("crm:interaction_list"),
        reverse("crm:interaction_detail", args=[d["interaction"].pk]), reverse("crm:feedback_list"),
        reverse("crm:feedback_create") + f"?customer={d['customer'].pk}",
        reverse("finance:account_list"), reverse("finance:account_detail", args=[Account.objects.get(code="1100").pk]),
        reverse("finance:journal_list"), reverse("finance:journal_detail", args=[journal.pk]),
        reverse("finance:journal_create"), reverse("finance:expense_list"),
        reverse("finance:expense_detail", args=[d["expense"].pk]), reverse("finance:expense_create"),
        reverse("finance:reports"), reverse("finance:reports") + "?report=tb", reverse("finance:reports") + "?report=vat",
        reverse("finance:reports") + "?report=ar", reverse("finance:reports") + "?report=ap",
        reverse("hr:department_list"), reverse("hr:employee_list"),
        reverse("hr:employee_detail", args=[d["employee"].pk]), reverse("hr:employee_create"),
        reverse("hr:leave_list"), reverse("hr:leave_detail", args=[d["leave"].pk]), reverse("hr:leave_create"),
        reverse("core:dashboard"),
    ]


def test_every_module_page_renders_for_admin(client, admin_user, data):
    login_verified(client, admin_user)
    for url in _pages(data):
        response = client.get(url)
        assert response.status_code == 200, f"{url} -> {response.status_code}"


def test_customer_360_shows_balance_and_csat(client, admin_user, data):
    login_verified(client, admin_user)
    html = client.get(reverse("crm:customer_detail", args=[data["customer"].pk])).content.decode()
    assert "Al Fair Supermarket" in html and "4.0 / 5" in html


def test_dashboard_lists_low_stock(client, admin_user):
    wh = WarehouseFactory()
    ProductFactory(sku="LOW-1", reorder_level=Decimal("50"))
    login_verified(client, admin_user)
    receive_stock(ProductFactory(sku="OK-1", reorder_level=0), wh, 5, 1)
    assert b"LOW-1" in client.get(reverse("core:dashboard")).content


@pytest.mark.parametrize("role,url_name,expected", [
    ("SalesOfficer", "purchasing:po_create", 403),
    ("SalesOfficer", "finance:journal_create", 403),
    ("SalesOfficer", "sales:invoice_create", 200),
    ("Storekeeper", "sales:invoice_create", 403),
    ("Storekeeper", "inventory:stock_operation", 200),
    ("HROfficer", "inventory:product_list", 403),
    ("HROfficer", "hr:employee_create", 200),
    ("Viewer", "sales:invoice_list", 200),
    ("Viewer", "sales:invoice_create", 403),
    ("Viewer", "hr:employee_list", 403),
    ("Manager", "purchasing:po_create", 200),
])
def test_role_access_to_pages(client, make_user, role, url_name, expected):
    login_verified(client, make_user(f"{role.lower()}@alwadi.om", roles=[role]))
    assert client.get(reverse(url_name)).status_code == expected


def test_invoice_ui_posts_and_blocks_on_stock(client, make_user):
    wh = WarehouseFactory()
    product = ProductFactory(sale_price=Decimal("5.000"))
    receive_stock(product, wh, 4, 2)
    customer = CustomerFactory()
    login_verified(client, make_user("sales@alwadi.om", roles=["SalesOfficer"]))
    base = {"customer": customer.pk, "warehouse": wh.pk, "invoice_date": "2026-05-01",
            "lines-TOTAL_FORMS": "2", "lines-INITIAL_FORMS": "0", "lines-0-product": product.pk}
    blocked = client.post(reverse("sales:invoice_create"), {**base, "lines-0-quantity": "9"})
    assert blocked.status_code == 200 and b"Insufficient stock" in blocked.content
    ok = client.post(reverse("sales:invoice_create"), {**base, "lines-0-quantity": "2"})
    assert ok.status_code == 302
    from sales.models import Invoice

    assert Invoice.objects.get().total == Decimal("10.500")


def test_po_ui_flow(client, make_user):
    wh = WarehouseFactory()
    product = ProductFactory()
    supplier = SupplierFactory()
    manager = make_user("mgr@alwadi.om", roles=["Manager"])
    login_verified(client, manager)
    response = client.post(reverse("purchasing:po_create"), {
        "supplier": supplier.pk, "warehouse": wh.pk, "lines-TOTAL_FORMS": "1", "lines-INITIAL_FORMS": "0",
        "lines-0-product": product.pk, "lines-0-quantity": "12", "lines-0-unit_cost": "1.250"})
    assert response.status_code == 302
    from purchasing.models import PurchaseOrder

    po = PurchaseOrder.objects.get()
    assert client.post(reverse("purchasing:po_approve", args=[po.pk])).status_code == 302
    client.post(reverse("purchasing:po_receive", args=[po.pk]), {f"qty_{po.lines.get().pk}": "12"})
    po.refresh_from_db()
    assert po.status == "RECEIVED"


def test_manual_journal_ui_rejects_unbalanced(client, admin_user):
    from finance.models import Account

    login_verified(client, admin_user)
    bank, capital = Account.objects.get(code="1010"), Account.objects.get(code="3000")
    response = client.post(reverse("finance:journal_create"), {
        "entry_date": "2026-01-05", "description": "Capital", "lines-TOTAL_FORMS": "2", "lines-INITIAL_FORMS": "0",
        "lines-0-account": bank.pk, "lines-0-debit": "100", "lines-1-account": capital.pk, "lines-1-credit": "90"})
    assert response.status_code == 200 and b"does not balance" in response.content


def test_leave_approval_ui(client, make_user):
    employee = EmployeeFactory()
    leave = submit_leave_request(employee, "SICK", datetime.date(2026, 3, 1), datetime.date(2026, 3, 2))
    login_verified(client, make_user("hr@alwadi.om", roles=["HROfficer"]))
    client.post(reverse("hr:leave_approve", args=[leave.pk]), {"note": "Get well"})
    leave.refresh_from_db()
    assert leave.status == "APPROVED"
