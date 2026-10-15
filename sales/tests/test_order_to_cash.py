"""Integration test of the full order-to-cash flow across crm, sales, inventory and finance."""
import datetime
from decimal import Decimal

import pytest

from core.factories import CustomerFactory, ProductFactory, WarehouseFactory
from finance import chart
from finance.services import account_balance, ar_aging, trial_balance
from inventory.services import InsufficientStock, receive_stock, stock_on_hand
from inventory.models import StockMovement
from sales import services
from sales.models import Invoice, SalesOrder

pytestmark = pytest.mark.django_db
D0 = datetime.date(2026, 4, 1)


@pytest.fixture
def setup():
    wh = WarehouseFactory(code="MCT")
    customer = CustomerFactory(name="Lulu Hypermarket Bausher", payment_terms_days=30)
    tea = ProductFactory(sku="TEA-100", cost_price=Decimal("1.200"), sale_price=Decimal("2.000"))
    soap = ProductFactory(sku="SOAP-6", cost_price=Decimal("0.500"), sale_price=Decimal("0.900"))
    receive_stock(tea, wh, 100, Decimal("1.200"), update_average_cost=False)
    receive_stock(soap, wh, 50, Decimal("0.500"), update_average_cost=False)
    return wh, customer, tea, soap


def test_full_order_to_cash(setup, make_user):
    wh, customer, tea, soap = setup
    sales_officer = make_user("sales@alwadi.om", roles=["SalesOfficer"])

    order = services.create_sales_order(
        customer, wh, [{"product": tea, "quantity": 10, "discount_pct": 10}, {"product": soap, "quantity": 20}],
        user=sales_officer, order_date=D0)
    # tea: 10 x 2.000 = 20.000 less 10% = 18.000 ; soap: 20 x 0.900 = 18.000
    assert order.subtotal == Decimal("36.000") and order.vat_amount == Decimal("1.800")
    services.confirm_sales_order(order)
    invoice = services.invoice_sales_order(order, user=sales_officer, invoice_date=D0)
    order.refresh_from_db()
    assert order.status == SalesOrder.Status.INVOICED

    # Invoice: totals, 5% VAT per line, due date from payment terms.
    assert invoice.total == Decimal("37.800")
    assert [line.line_vat for line in invoice.lines.all()] == [Decimal("0.900"), Decimal("0.900")]
    assert invoice.due_date == D0 + datetime.timedelta(days=30)
    assert invoice.cost_total == Decimal("22.000")

    # Stock OUT movements reference the invoice.
    assert stock_on_hand(tea, wh) == Decimal("90.000")
    assert StockMovement.objects.filter(reference_type="INV", reference_id=invoice.pk).count() == 2

    # Journal: AR / Sales / VAT output / COGS / Inventory.
    assert account_balance(chart.ACCOUNTS_RECEIVABLE) == Decimal("37.800")
    assert account_balance(chart.SALES) == Decimal("36.000")
    assert account_balance(chart.VAT_OUTPUT) == Decimal("1.800")
    assert account_balance(chart.COGS) == Decimal("22.000")

    # Partial then final payment.
    services.record_payment(invoice, Decimal("20.000"), D0 + datetime.timedelta(days=5))
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.PARTIAL and invoice.balance_due == Decimal("17.800")
    aging = ar_aging(D0 + datetime.timedelta(days=45))
    assert aging["totals"]["d1_30"] == Decimal("17.800")
    services.record_payment(invoice, Decimal("17.800"), D0 + datetime.timedelta(days=40), method="CASH")
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.PAID
    assert account_balance(chart.ACCOUNTS_RECEIVABLE) == 0
    assert trial_balance()["balanced"]


def test_invoice_blocked_when_stock_insufficient(setup):
    wh, customer, tea, soap = setup
    with pytest.raises(InsufficientStock):
        services.create_invoice(customer, wh, [{"product": tea, "quantity": 60}, {"product": tea, "quantity": 50}])
    assert not Invoice.objects.exists()
    assert stock_on_hand(tea, wh) == Decimal("100.000")


def test_invoice_in_other_warehouse_is_blocked(setup):
    wh, customer, tea, soap = setup
    with pytest.raises(InsufficientStock):
        services.create_invoice(customer, WarehouseFactory(code="SOH"), [{"product": tea, "quantity": 1}])


def test_overpayment_is_rejected(setup):
    wh, customer, tea, _ = setup
    invoice = services.create_invoice(customer, wh, [{"product": tea, "quantity": 1}])
    with pytest.raises(services.SalesError):
        services.record_payment(invoice, invoice.total + Decimal("0.001"))
    with pytest.raises(services.SalesError):
        services.record_payment(invoice, 0)


def test_credit_note_returns_stock_and_reverses_revenue(setup):
    wh, customer, tea, soap = setup
    invoice = services.create_invoice(customer, wh, [{"product": tea, "quantity": 10}], invoice_date=D0)
    line = invoice.lines.get()
    note = services.create_credit_note(invoice, [{"invoice_line": line, "quantity": 4}], "Damaged in transit",
                                       credit_date=D0)
    assert note.subtotal == Decimal("8.000") and note.vat_amount == Decimal("0.400")
    assert stock_on_hand(tea, wh) == Decimal("94.000")
    invoice.refresh_from_db()
    assert invoice.balance_due == Decimal("12.600") and invoice.status == Invoice.Status.PARTIAL
    assert account_balance(chart.SALES_RETURNS) == Decimal("-8.000")
    assert account_balance(chart.VAT_OUTPUT) == Decimal("0.600")
    with pytest.raises(services.SalesError):
        services.create_credit_note(invoice, [{"invoice_line": line, "quantity": 7}], "too many")
    assert trial_balance()["balanced"]


def test_invoice_posting_is_atomic(setup, monkeypatch):
    wh, customer, tea, _ = setup

    def boom(*a, **k):
        raise RuntimeError("ledger down")

    monkeypatch.setattr(services.finance, "post_journal", boom)
    with pytest.raises(RuntimeError):
        services.create_invoice(customer, wh, [{"product": tea, "quantity": 5}])
    assert not Invoice.objects.exists()
    assert stock_on_hand(tea, wh) == Decimal("100.000")


def test_order_state_rules(setup):
    wh, customer, tea, _ = setup
    order = services.create_sales_order(customer, wh, [{"product": tea, "quantity": 1}])
    with pytest.raises(services.SalesError):
        services.invoice_sales_order(order)
    services.cancel_sales_order(order)
    with pytest.raises(services.SalesError):
        services.confirm_sales_order(order)
    with pytest.raises(services.SalesError):
        services.create_sales_order(customer, wh, [{"product": tea, "quantity": 1, "discount_pct": 120}])


def test_inactive_customer_cannot_be_invoiced(setup):
    wh, customer, tea, _ = setup
    customer.is_active = False
    customer.save()
    with pytest.raises(services.SalesError):
        services.create_invoice(customer, wh, [{"product": tea, "quantity": 1}])


def test_customer_outstanding(setup):
    wh, customer, tea, _ = setup
    invoice = services.create_invoice(customer, wh, [{"product": tea, "quantity": 5}])
    services.record_payment(invoice, Decimal("4.500"))
    assert services.customer_outstanding(customer) == Decimal("6.000")


def test_update_draft_sales_order(setup):
    wh, customer, tea, soap = setup
    order = services.create_sales_order(customer, wh, [{"product": tea, "quantity": 1}])
    services.update_sales_order(order, customer, wh, [{"product": soap, "quantity": 10}], notes="Changed")
    order.refresh_from_db()
    assert list(order.lines.values_list("product", flat=True)) == [soap.pk]
    assert order.subtotal == Decimal("9.000")
    services.confirm_sales_order(order)
    with pytest.raises(services.SalesError):
        services.update_sales_order(order, customer, wh, [{"product": tea, "quantity": 1}])
