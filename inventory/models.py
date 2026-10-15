from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel, money_field, quantity_field


class Category(TimeStampedModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Warehouse(TimeStampedModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=50)
    address = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Product(TimeStampedModel):
    class Unit(models.TextChoices):
        PIECE = "PCS", "Piece"
        CARTON = "CTN", "Carton"
        BOX = "BOX", "Box"
        PACK = "PACK", "Pack"
        BAG = "BAG", "Bag"
        KG = "KG", "Kilogram"
        LITRE = "LTR", "Litre"
        BOTTLE = "BTL", "Bottle"

    sku = models.CharField("SKU", max_length=30, unique=True)
    name = models.CharField(max_length=150)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    unit = models.CharField(max_length=5, choices=Unit.choices, default=Unit.PIECE)
    barcode = models.CharField(max_length=30, blank=True)
    cost_price = money_field(help_text="Weighted average cost (OMR), updated on goods receipt")
    sale_price = money_field(help_text="Selling price excluding VAT (OMR)")
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    reorder_level = quantity_field()
    reorder_quantity = quantity_field()
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["sku"]
        indexes = [models.Index(fields=["name"])]

    def __str__(self):
        return f"{self.sku} - {self.name}"

    @property
    def on_hand(self):
        if hasattr(self, "_on_hand"):
            return self._on_hand
        from .services import stock_on_hand

        return stock_on_hand(self)

    @property
    def margin_pct(self):
        if not self.sale_price:
            return None
        return (self.sale_price - self.cost_price) / self.sale_price * 100


class StockMovement(models.Model):
    """Signed stock delta for one product in one warehouse. Stock on hand = SUM(quantity)."""

    class Type(models.TextChoices):
        IN = "IN", "Stock in"
        OUT = "OUT", "Stock out"
        TRANSFER = "TRANSFER", "Transfer"
        ADJUST = "ADJUST", "Adjustment"

    class Reference(models.TextChoices):
        GOODS_RECEIPT = "GRN", "Goods receipt"
        INVOICE = "INV", "Sales invoice"
        CREDIT_NOTE = "CN", "Credit note"
        ADJUSTMENT = "ADJ", "Stock adjustment"
        TRANSFER = "TRF", "Warehouse transfer"
        OPENING = "OPEN", "Opening stock"
        MANUAL = "MAN", "Manual entry"

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="movements")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="movements")
    movement_type = models.CharField(max_length=10, choices=Type.choices)
    quantity = quantity_field(help_text="Positive = into the warehouse, negative = out of it")
    unit_cost = money_field()
    reference_type = models.CharField(max_length=5, choices=Reference.choices, default=Reference.MANUAL)
    reference_id = models.BigIntegerField(null=True, blank=True)
    reference_no = models.CharField(max_length=40, blank=True)
    movement_date = models.DateTimeField(default=timezone.now, db_index=True)
    note = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-movement_date", "-id"]
        indexes = [
            models.Index(fields=["product", "warehouse"]),
            models.Index(fields=["reference_type", "reference_id"]),
        ]

    def __str__(self):
        return f"{self.get_movement_type_display()} {self.quantity} x {self.product.sku} @ {self.warehouse.code}"

    @property
    def value(self):
        return self.quantity * self.unit_cost
