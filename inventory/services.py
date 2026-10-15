"""Inventory business logic. Stock on hand is never stored: it is the sum of signed movements."""
from decimal import Decimal

from django.db import transaction
from django.db.models import DecimalField, F, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from core.money import D, q3

from .models import Product, StockMovement, Warehouse

ZERO_QTY = Decimal("0.000")


class InsufficientStock(Exception):
    """Raised when an issue would take stock below zero. `shortages` lists (product, needed, available)."""

    def __init__(self, shortages):
        self.shortages = shortages
        detail = "; ".join(f"{p.sku}: need {n}, available {a}" for p, n, a in shortages)
        super().__init__(f"Insufficient stock - {detail}")


def stock_on_hand(product, warehouse=None, as_of=None):
    qs = StockMovement.objects.filter(product=product)
    if warehouse is not None:
        qs = qs.filter(warehouse=warehouse)
    if as_of is not None:
        qs = qs.filter(movement_date__lte=as_of)
    return qs.aggregate(total=Coalesce(Sum("quantity"), Value(ZERO_QTY)))["total"]


def _on_hand_subquery(warehouse=None):
    movements = StockMovement.objects.filter(product=OuterRef("pk"))
    if warehouse is not None:
        movements = movements.filter(warehouse=warehouse)
    total = movements.values("product").annotate(total=Sum("quantity")).values("total")
    return Coalesce(Subquery(total, output_field=DecimalField(max_digits=14, decimal_places=3)), Value(ZERO_QTY))


def products_with_stock(warehouse=None, queryset=None):
    """Products annotated with `on_hand_qty` (optionally for one warehouse)."""
    queryset = queryset if queryset is not None else Product.objects.all()
    return queryset.select_related("category").annotate(on_hand_qty=_on_hand_subquery(warehouse))


def low_stock_products(warehouse=None):
    """Active products at or below their reorder level - shown as alerts on the dashboard."""
    qs = (
        products_with_stock(warehouse, Product.objects.filter(is_active=True))
        .filter(on_hand_qty__lte=F("reorder_level"))
        .order_by("on_hand_qty", "sku")
    )
    result = list(qs)
    for product in result:
        product._on_hand = product.on_hand_qty
    return result


def stock_matrix(products=None):
    """{product_id: {warehouse_id: qty}} for the stock-levels page."""
    qs = StockMovement.objects.values("product_id", "warehouse_id").annotate(qty=Sum("quantity"))
    if products is not None:
        qs = qs.filter(product__in=products)
    matrix = {}
    for row in qs:
        matrix.setdefault(row["product_id"], {})[row["warehouse_id"]] = row["qty"]
    return matrix


def inventory_value(warehouse=None):
    """Value of stock on hand at weighted average cost."""
    total = Decimal("0")
    for product in products_with_stock(warehouse):
        if product.on_hand_qty > 0:
            total += product.on_hand_qty * product.cost_price
    return q3(total)


def lock_products(product_ids):
    """Lock product rows (in id order, avoiding deadlocks) to serialise concurrent stock checks."""
    return {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=sorted(set(product_ids))).order_by("pk")}


def check_availability(warehouse, requirements):
    """requirements: {product: qty}. Raises InsufficientStock listing every shortage."""
    shortages = []
    on_hand = dict(
        StockMovement.objects.filter(warehouse=warehouse, product__in=[p.pk for p in requirements])
        .values("product").annotate(total=Sum("quantity")).values_list("product", "total")
    )
    for product, needed in requirements.items():
        available = on_hand.get(product.pk, ZERO_QTY)
        if D(needed) > available:
            shortages.append((product, q3(needed), available))
    if shortages:
        raise InsufficientStock(shortages)


def _movement(product, warehouse, movement_type, quantity, unit_cost, reference_type, reference_id,
              reference_no, user, movement_date, note):
    return StockMovement.objects.create(
        product=product,
        warehouse=warehouse,
        movement_type=movement_type,
        quantity=q3(quantity),
        unit_cost=q3(unit_cost if unit_cost is not None else product.cost_price),
        reference_type=reference_type,
        reference_id=reference_id,
        reference_no=reference_no,
        movement_date=movement_date or timezone.now(),
        note=note,
        created_by=user,
    )


@transaction.atomic
def receive_stock(product, warehouse, quantity, unit_cost, reference_type=StockMovement.Reference.MANUAL,
                  reference_id=None, reference_no="", user=None, movement_date=None, note="",
                  update_average_cost=True):
    """Stock IN. Updates the product's weighted average cost."""
    quantity = D(quantity)
    if quantity <= 0:
        raise ValueError("Received quantity must be positive.")
    product = Product.objects.select_for_update().get(pk=product.pk)
    if update_average_cost:
        current = stock_on_hand(product)
        if current > 0:
            new_cost = (current * product.cost_price + quantity * D(unit_cost)) / (current + quantity)
        else:
            new_cost = D(unit_cost)
        product.cost_price = q3(new_cost)
        product.save(update_fields=["cost_price", "updated_at"])
    return _movement(product, warehouse, StockMovement.Type.IN, quantity, unit_cost, reference_type,
                     reference_id, reference_no, user, movement_date, note)


@transaction.atomic
def issue_stock(product, warehouse, quantity, reference_type=StockMovement.Reference.MANUAL, reference_id=None,
                reference_no="", user=None, movement_date=None, note="", unit_cost=None, check=True):
    """Stock OUT (stored as a negative quantity). Blocks when stock would go negative."""
    quantity = D(quantity)
    if quantity <= 0:
        raise ValueError("Issued quantity must be positive.")
    lock_products([product.pk])
    if check:
        check_availability(warehouse, {product: quantity})
    return _movement(product, warehouse, StockMovement.Type.OUT, -quantity, unit_cost, reference_type,
                     reference_id, reference_no, user, movement_date, note)


@transaction.atomic
def transfer_stock(product, from_warehouse, to_warehouse, quantity, user=None, movement_date=None, note=""):
    """Move stock between warehouses: two TRANSFER rows (-source, +destination)."""
    if from_warehouse == to_warehouse:
        raise ValueError("Source and destination warehouse must differ.")
    quantity = D(quantity)
    if quantity <= 0:
        raise ValueError("Transfer quantity must be positive.")
    lock_products([product.pk])
    check_availability(from_warehouse, {product: quantity})
    from core.numbering import next_number

    number = next_number("TRF")
    out = _movement(product, from_warehouse, StockMovement.Type.TRANSFER, -quantity, None,
                    StockMovement.Reference.TRANSFER, None, number, user, movement_date,
                    note or f"To {to_warehouse.code}")
    inn = _movement(product, to_warehouse, StockMovement.Type.TRANSFER, quantity, None,
                    StockMovement.Reference.TRANSFER, None, number, user, movement_date,
                    note or f"From {from_warehouse.code}")
    return out, inn


@transaction.atomic
def adjust_stock(product, warehouse, quantity_delta, reason, user=None, movement_date=None, post_to_ledger=True):
    """Stock count correction (signed). Posts the value difference to the ledger."""
    delta = D(quantity_delta)
    if delta == 0:
        raise ValueError("Adjustment quantity cannot be zero.")
    lock_products([product.pk])
    if delta < 0:
        check_availability(warehouse, {product: -delta})
    from core.numbering import next_number

    number = next_number("ADJ")
    movement = _movement(product, warehouse, StockMovement.Type.ADJUST, delta, None,
                         StockMovement.Reference.ADJUSTMENT, None, number, user, movement_date, reason)
    if post_to_ledger:
        from finance import services as finance

        finance.post_stock_adjustment(movement, user=user)
    return movement


@transaction.atomic
def record_opening_stock(product, warehouse, quantity, unit_cost, user=None, movement_date=None):
    """Opening balance from a legacy system (data migration)."""
    return receive_stock(product, warehouse, quantity, unit_cost, StockMovement.Reference.OPENING,
                         reference_no="OPENING", user=user, movement_date=movement_date, note="Opening stock")


def warehouses():
    return Warehouse.objects.filter(is_active=True)

