from decimal import Decimal

import pytest

from core.factories import CustomerFactory, ProductFactory, WarehouseFactory
from crm import services
from crm.models import Interaction
from inventory.services import receive_stock
from sales.services import create_invoice, record_payment

pytestmark = pytest.mark.django_db


def test_complaints_open_and_can_be_closed():
    customer = CustomerFactory()
    complaint = services.log_interaction(customer, Interaction.Type.COMPLAINT, "Late delivery")
    call = services.log_interaction(customer, Interaction.Type.CALL, "Price enquiry")
    assert complaint.status == Interaction.Status.OPEN
    assert call.status == Interaction.Status.CLOSED
    services.close_interaction(complaint)
    assert complaint.status == Interaction.Status.CLOSED


def test_feedback_score_validated():
    customer = CustomerFactory()
    with pytest.raises(ValueError):
        services.record_feedback(customer, 6)
    with pytest.raises(ValueError):
        services.record_feedback(customer, 0)
    services.record_feedback(customer, 4)
    services.record_feedback(customer, 5)
    assert services.average_csat(customer.feedback.all()) == Decimal("4.5")
    assert services.average_csat(CustomerFactory().feedback.all()) is None


def test_feedback_invoice_must_belong_to_customer():
    wh = WarehouseFactory()
    product = ProductFactory()
    receive_stock(product, wh, 10, 1)
    a, b = CustomerFactory(), CustomerFactory()
    invoice = create_invoice(a, wh, [{"product": product, "quantity": 1}])
    with pytest.raises(ValueError):
        services.record_feedback(b, 3, invoice=invoice)


def test_customer_360_aggregates():
    wh = WarehouseFactory()
    product = ProductFactory(sale_price=Decimal("10.000"))
    receive_stock(product, wh, 100, 5)
    customer = CustomerFactory(credit_limit=Decimal("500"))
    invoice = create_invoice(customer, wh, [{"product": product, "quantity": 3}])
    record_payment(invoice, Decimal("10.000"))
    services.record_feedback(customer, 3)
    services.log_interaction(customer, Interaction.Type.COMPLAINT, "Broken seal")
    data = services.customer_360(customer)
    assert data["total_revenue"] == Decimal("30.000")
    assert data["outstanding"] == Decimal("21.500")
    assert data["avg_csat"] == Decimal("3")
    assert data["open_complaints"] == 1
    assert data["credit_available"] == Decimal("478.500")
    assert data["invoice_count"] == 1
