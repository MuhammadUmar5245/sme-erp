from decimal import Decimal

import pytest

from core.factories import ProductFactory, WarehouseFactory
from finance.models import JournalEntry
from finance.services import account_balance
from inventory import services
from inventory.models import StockMovement

pytestmark = pytest.mark.django_db


@pytest.fixture
def product():
    return ProductFactory(cost_price=Decimal("2.000"), reorder_level=Decimal("20"))


@pytest.fixture
def wh():
    return WarehouseFactory(code="MCT")


def test_stock_is_sum_of_movements(product, wh):
    services.receive_stock(product, wh, 50, Decimal("2.000"))
    services.issue_stock(product, wh, 15)
    assert services.stock_on_hand(product, wh) == Decimal("35.000")
    assert StockMovement.objects.filter(product=product).count() == 2


def test_issue_blocks_when_insufficient(product, wh):
    services.receive_stock(product, wh, 5, 2)
    with pytest.raises(services.InsufficientStock) as exc:
        services.issue_stock(product, wh, 6)
    assert exc.value.shortages[0][1] == Decimal("6.000")
    assert services.stock_on_hand(product, wh) == Decimal("5.000")


def test_receive_updates_weighted_average_cost(product, wh):
    services.receive_stock(product, wh, 10, Decimal("2.000"))
    services.receive_stock(product, wh, 10, Decimal("4.000"))
    product.refresh_from_db()
    assert product.cost_price == Decimal("3.000")


def test_transfer_moves_stock_between_warehouses(product, wh):
    sohar = WarehouseFactory(code="SOH")
    services.receive_stock(product, wh, 30, 2)
    out, inn = services.transfer_stock(product, wh, sohar, 12)
    assert out.reference_no == inn.reference_no
    assert services.stock_on_hand(product, wh) == Decimal("18.000")
    assert services.stock_on_hand(product, sohar) == Decimal("12.000")
    assert services.stock_on_hand(product) == Decimal("30.000")


def test_transfer_requires_stock_and_distinct_warehouses(product, wh):
    with pytest.raises(ValueError):
        services.transfer_stock(product, wh, wh, 1)
    with pytest.raises(services.InsufficientStock):
        services.transfer_stock(product, wh, WarehouseFactory(code="SOH"), 1)


def test_adjustment_posts_to_ledger(product, wh):
    services.receive_stock(product, wh, 10, Decimal("2.000"))
    services.adjust_stock(product, wh, -3, "Damaged cartons")
    assert services.stock_on_hand(product, wh) == Decimal("7.000")
    entry = JournalEntry.objects.get(source_type="ADJ")
    assert entry.total_debit == entry.total_credit == Decimal("6.000")
    assert account_balance("5100") == Decimal("6.000")


def test_adjustment_rejects_zero(product, wh):
    with pytest.raises(ValueError):
        services.adjust_stock(product, wh, 0, "nothing")


def test_low_stock_list(wh):
    low = ProductFactory(reorder_level=Decimal("20"))
    ok = ProductFactory(reorder_level=Decimal("5"))
    services.receive_stock(low, wh, 10, 1)
    services.receive_stock(ok, wh, 10, 1)
    result = services.low_stock_products()
    assert low in result and ok not in result
    assert result[0].on_hand == Decimal("10.000")


def test_inventory_value_and_matrix(product, wh):
    services.receive_stock(product, wh, 10, Decimal("2.000"))
    assert services.inventory_value() == Decimal("20.000")
    assert services.stock_matrix()[product.pk][wh.pk] == Decimal("10.000")


def test_negative_quantities_rejected(product, wh):
    with pytest.raises(ValueError):
        services.receive_stock(product, wh, -1, 1)
    with pytest.raises(ValueError):
        services.issue_stock(product, wh, 0)


def test_opening_stock(product, wh):
    movement = services.record_opening_stock(product, wh, 40, Decimal("1.500"))
    assert movement.reference_type == "OPEN"
    assert services.stock_on_hand(product) == Decimal("40.000")
