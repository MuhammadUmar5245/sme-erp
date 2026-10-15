from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel, money_field, quantity_field
from core.money import q3, vat_amount


class Supplier(TimeStampedModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150, db_index=True)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    city = models.CharField(max_length=50, default="Muscat")
    country = models.CharField(max_length=50, default="Oman")
    address = models.CharField(max_length=200, blank=True)
    vat_number = models.CharField("VAT number", max_length=20, blank=True)
    payment_terms_days = models.PositiveSmallIntegerField(default=30)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class PurchaseOrder(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        APPROVED = "APPROVED", "Approved"
        RECEIVED = "RECEIVED", "Received"
        BILLED = "BILLED", "Billed"
        CANCELLED = "CANCELLED", "Cancelled"

    number = models.CharField(max_length=30, unique=True, editable=False)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    warehouse = models.ForeignKey("inventory.Warehouse", on_delete=models.PROTECT, related_name="purchase_orders")
    order_date = models.DateField(default=timezone.localdate, db_index=True)
    expected_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="+")
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    subtotal = money_field()
    vat_amount = money_field()
    total = money_field()

    class Meta:
        ordering = ["-order_date", "-id"]
        permissions = [
            ("approve_purchaseorder", "Can approve purchase orders"),
            ("receive_purchaseorder", "Can receive goods against purchase orders"),
        ]

    def __str__(self):
        return self.number

    @property
    def is_fully_received(self):
        return all(line.received_quantity >= line.quantity for line in self.lines.all())


class PurchaseOrderLine(models.Model):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("inventory.Product", on_delete=models.PROTECT, related_name="purchase_lines")
    quantity = quantity_field()
    unit_cost = money_field()
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    received_quantity = quantity_field()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.product.sku} x {self.quantity}"

    @property
    def line_subtotal(self):
        return q3(self.quantity * self.unit_cost)

    @property
    def line_vat(self):
        return vat_amount(self.line_subtotal, self.vat_rate)

    @property
    def line_total(self):
        return self.line_subtotal + self.line_vat

    @property
    def remaining_quantity(self):
        return max(self.quantity - self.received_quantity, 0)


class GoodsReceipt(TimeStampedModel):
    number = models.CharField(max_length=30, unique=True, editable=False)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name="receipts")
    warehouse = models.ForeignKey("inventory.Warehouse", on_delete=models.PROTECT, related_name="receipts")
    receipt_date = models.DateField(default=timezone.localdate, db_index=True)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-receipt_date", "-id"]

    def __str__(self):
        return self.number

    @property
    def total_value(self):
        return sum((line.quantity * line.unit_cost for line in self.lines.all()), 0)


class GoodsReceiptLine(models.Model):
    receipt = models.ForeignKey(GoodsReceipt, on_delete=models.CASCADE, related_name="lines")
    po_line = models.ForeignKey(PurchaseOrderLine, on_delete=models.PROTECT, related_name="receipt_lines")
    product = models.ForeignKey("inventory.Product", on_delete=models.PROTECT, related_name="+")
    quantity = quantity_field()
    unit_cost = money_field()

    class Meta:
        ordering = ["id"]

    @property
    def line_value(self):
        return q3(self.quantity * self.unit_cost)


class SupplierBill(TimeStampedModel):
    class Status(models.TextChoices):
        UNPAID = "UNPAID", "Unpaid"
        PARTIAL = "PARTIAL", "Partially paid"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    number = models.CharField(max_length=30, unique=True, editable=False)
    supplier_invoice_no = models.CharField("Supplier invoice no.", max_length=40)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="bills")
    purchase_order = models.ForeignKey(PurchaseOrder, null=True, blank=True, on_delete=models.PROTECT,
                                       related_name="bills")
    bill_date = models.DateField(default=timezone.localdate, db_index=True)
    due_date = models.DateField(db_index=True)
    subtotal = money_field()
    vat_amount = money_field()
    total = money_field()
    amount_paid = money_field()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.UNPAID, db_index=True)
    journal_entry = models.ForeignKey("finance.JournalEntry", null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name="+")

    class Meta:
        ordering = ["-bill_date", "-id"]

    def __str__(self):
        return f"{self.number} ({self.supplier_invoice_no})"

    @property
    def balance_due(self):
        return self.total - self.amount_paid


class SupplierPayment(TimeStampedModel):
    class Method(models.TextChoices):
        BANK = "BANK", "Bank transfer"
        CASH = "CASH", "Cash"
        CHEQUE = "CHEQUE", "Cheque"

    number = models.CharField(max_length=30, unique=True, editable=False)
    bill = models.ForeignKey(SupplierBill, on_delete=models.PROTECT, related_name="payments")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="payments")
    payment_date = models.DateField(default=timezone.localdate, db_index=True)
    amount = money_field()
    method = models.CharField(max_length=6, choices=Method.choices, default=Method.BANK)
    reference = models.CharField(max_length=60, blank=True)
    journal_entry = models.ForeignKey("finance.JournalEntry", null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name="+")

    class Meta:
        ordering = ["-payment_date", "-id"]

    def __str__(self):
        return self.number
