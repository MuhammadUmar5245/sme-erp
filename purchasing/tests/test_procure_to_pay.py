"""Integration test of the full procure-to-pay flow across purchasing, inventory and finance."""
import datetime
from decimal import Decimal

import pytest

from core.factories import ProductFactory, SupplierFactory, WarehouseFactory
from finance import chart
from finance.services import account_balance, ap_aging, trial_balance
from inventory.services import stock_on_hand
from purchasing import services
from purchasing.models import PurchaseOrder, SupplierBill

pytestmark = pytest.mark.django_db
D0 = datetime.date(2026, 3, 1)


@pytest.fixture
def setup():
    supplier = SupplierFactory(payment_terms_days=45)
    wh = WarehouseFactory(code="MCT")
    rice = ProductFactory(sku="RICE-5KG", cost_price=Decimal("2.000"))
    oil = ProductFactory(sku="OIL-1L", cost_price=Decimal("0.800"))
    order = services.create_purchase_order(
        supplier, wh, [{"product": rice, "quantity": 100, "unit_cost": "2.100"},
                       {"product": oil, "quantity": 200, "unit_cost": "0.750"}], order_date=D0)
    return supplier, wh, rice, oil, order


def test_full_procure_to_pay(setup, make_user):
    supplier, wh, rice, oil, order = setup
    manager = make_user("mgr@alwadi.om", roles=["Manager"])
    assert order.subtotal == Decimal("360.000") and order.vat_amount == Decimal("18.000")

    services.approve_purchase_order(order, manager)
    order.refresh_from_db()
    assert order.status == PurchaseOrder.Status.APPROVED and order.approved_by == manager

    # Partial receipt keeps the order approved.
    rice_line = order.lines.get(product=rice)
    services.receive_goods(order, {rice_line.pk: 60}, receipt_date=D0)
    order.refresh_from_db()
    assert order.status == PurchaseOrder.Status.APPROVED
    assert stock_on_hand(rice, wh) == Decimal("60.000")

    services.receive_goods(order, receipt_date=D0 + datetime.timedelta(days=2))  # the rest
    order.refresh_from_db()
    assert order.status == PurchaseOrder.Status.RECEIVED
    assert stock_on_hand(rice, wh) == Decimal("100.000")
    assert stock_on_hand(oil, wh) == Decimal("200.000")
    assert account_balance(chart.INVENTORY) == Decimal("360.000")
    assert account_balance(chart.GRNI) == Decimal("360.000")

    bill = services.create_bill_from_po(order, "SUP-INV-778", bill_date=D0 + datetime.timedelta(days=3))
    order.refresh_from_db()
    assert order.status == PurchaseOrder.Status.BILLED
    assert bill.total == Decimal("378.000")
    assert bill.due_date == D0 + datetime.timedelta(days=48)
    assert account_balance(chart.GRNI) == 0
    assert account_balance(chart.VAT_INPUT) == Decimal("18.000")
    assert account_balance(chart.ACCOUNTS_PAYABLE) == Decimal("378.000")

    services.pay_supplier_bill(bill, Decimal("200"), D0 + datetime.timedelta(days=10))
    bill.refresh_from_db()
    assert bill.status == SupplierBill.Status.PARTIAL
    aging = ap_aging(D0 + datetime.timedelta(days=60))
    assert aging["totals"]["total"] == Decimal("178.000")
    assert aging["totals"]["d1_30"] == Decimal("178.000")

    services.pay_supplier_bill(bill, Decimal("178"), D0 + datetime.timedelta(days=20), method="CASH")
    bill.refresh_from_db()
    assert bill.status == SupplierBill.Status.PAID
    assert account_balance(chart.ACCOUNTS_PAYABLE) == 0
    assert account_balance(chart.BANK) == Decimal("-200.000")
    assert account_balance(chart.CASH) == Decimal("-178.000")
    assert trial_balance()["balanced"]


def test_cannot_receive_unapproved_order(setup):
    order = setup[4]
    with pytest.raises(services.PurchasingError):
        services.receive_goods(order)


def test_cannot_over_receive(setup):
    order = setup[4]
    services.approve_purchase_order(order)
    line = order.lines.first()
    with pytest.raises(services.PurchasingError):
        services.receive_goods(order, {line.pk: line.quantity + 1})


def test_receipt_is_atomic(setup, monkeypatch):
    """If the journal posting fails, no stock movement or receipt survives."""
    supplier, wh, rice, oil, order = setup
    services.approve_purchase_order(order)

    def boom(*args, **kwargs):
        raise RuntimeError("ledger down")

    monkeypatch.setattr(services.finance, "post_journal", boom)
    with pytest.raises(RuntimeError):
        services.receive_goods(order)
    assert stock_on_hand(rice, wh) == 0
    assert not order.receipts.exists()


def test_bill_rules(setup):
    order = setup[4]
    with pytest.raises(services.PurchasingError):
        services.create_bill_from_po(order, "X")
    services.approve_purchase_order(order)
    with pytest.raises(services.PurchasingError):
        services.approve_purchase_order(order)
    services.receive_goods(order)
    bill = services.create_bill_from_po(order, "X1")
    with pytest.raises(services.PurchasingError):
        services.pay_supplier_bill(bill, bill.total + 1)


def test_cancel_rules(setup):
    order = setup[4]
    services.cancel_purchase_order(order)
    order.refresh_from_db()
    assert order.status == PurchaseOrder.Status.CANCELLED
    with pytest.raises(services.PurchasingError):
        services.cancel_purchase_order(order)


def test_empty_or_invalid_orders_rejected(setup):
    supplier, wh, rice, *_ = setup
    with pytest.raises(services.PurchasingError):
        services.create_purchase_order(supplier, wh, [])
    with pytest.raises(services.PurchasingError):
        services.create_purchase_order(supplier, wh, [{"product": rice, "quantity": 0}])
