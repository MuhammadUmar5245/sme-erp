from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel, money_field, quantity_field
from core.money import q3, vat_amount


class SalesOrder(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        CONFIRMED = "CONFIRMED", "Confirmed"
        INVOICED = "INVOICED", "Invoiced"
        CANCELLED = "CANCELLED", "Cancelled"

    number = models.CharField(max_length=30, unique=True, editable=False)
    customer = models.ForeignKey("crm.Customer", on_delete=models.PROTECT, related_name="sales_orders")
    warehouse = models.ForeignKey("inventory.Warehouse", on_delete=models.PROTECT, related_name="sales_orders")
    order_date = models.DateField(default=timezone.localdate, db_index=True)
    delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True)
    salesperson = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="sales_orders")
    notes = models.TextField(blank=True)
    subtotal = money_field()
    vat_amount = money_field()
    total = money_field()

    class Meta:
        ordering = ["-order_date", "-id"]

    def __str__(self):
        return self.number


class LineAmountsMixin:
    @property
    def gross(self):
        return q3(self.quantity * self.unit_price)

    @property
    def net(self):
        return q3(self.gross * (100 - self.discount_pct) / 100)

    @property
    def vat(self):
        return vat_amount(self.net, self.vat_rate)


class SalesOrderLine(LineAmountsMixin, models.Model):
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("inventory.Product", on_delete=models.PROTECT, related_name="sales_order_lines")
    quantity = quantity_field()
    unit_price = money_field()
    discount_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5)

    class Meta:
        ordering = ["id"]


class Invoice(TimeStampedModel):
    """Tax invoice. Posting creates stock OUT movements and a journal entry in one transaction."""

    class Status(models.TextChoices):
        POSTED = "POSTED", "Posted (unpaid)"
        PARTIAL = "PARTIAL", "Partially paid"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    class Source(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        SALES_ORDER = "SO", "Sales order"
        POS = "POS", "Point of sale"
        IMPORT = "IMPORT", "Data import"

    number = models.CharField(max_length=30, unique=True, editable=False)
    customer = models.ForeignKey("crm.Customer", on_delete=models.PROTECT, related_name="invoices")
    sales_order = models.ForeignKey(SalesOrder, null=True, blank=True, on_delete=models.PROTECT,
                                    related_name="invoices")
    warehouse = models.ForeignKey("inventory.Warehouse", on_delete=models.PROTECT, related_name="invoices")
    invoice_date = models.DateField(default=timezone.localdate, db_index=True)
    due_date = models.DateField(db_index=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.POSTED, db_index=True)
    source = models.CharField(max_length=6, choices=Source.choices, default=Source.MANUAL)
    external_ref = models.CharField(max_length=60, blank=True, help_text="e.g. POS receipt number")
    salesperson = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="invoices")
    subtotal = money_field(help_text="Net of discounts, excluding VAT")
    vat_amount = money_field()
    total = money_field()
    cost_total = money_field(help_text="Cost of goods sold at weighted average cost")
    amount_paid = money_field()
    amount_credited = money_field()
    journal_entry = models.ForeignKey("finance.JournalEntry", null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name="+")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-invoice_date", "-id"]
        indexes = [models.Index(fields=["customer", "invoice_date"])]

    def __str__(self):
        return self.number

    @property
    def balance_due(self):
        return self.total - self.amount_paid - self.amount_credited

    @property
    def is_overdue(self):
        return self.balance_due > 0 and self.due_date < timezone.localdate()

    @property
    def gross_margin(self):
        return self.subtotal - self.cost_total


class InvoiceLine(LineAmountsMixin, models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("inventory.Product", on_delete=models.PROTECT, related_name="invoice_lines")
    description = models.CharField(max_length=200, blank=True)
    quantity = quantity_field()
    unit_price = money_field()
    discount_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    line_subtotal = money_field()
    line_vat = money_field()
    line_total = money_field()
    unit_cost = money_field()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.product.sku} x {self.quantity}"


class Payment(TimeStampedModel):
    class Method(models.TextChoices):
        CASH = "CASH", "Cash"
        BANK = "BANK", "Bank transfer"
        CARD = "CARD", "Card"
        CHEQUE = "CHEQUE", "Cheque"

    number = models.CharField(max_length=30, unique=True, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    customer = models.ForeignKey("crm.Customer", on_delete=models.PROTECT, related_name="payments")
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


class CreditNote(TimeStampedModel):
    number = models.CharField(max_length=30, unique=True, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="credit_notes")
    customer = models.ForeignKey("crm.Customer", on_delete=models.PROTECT, related_name="credit_notes")
    credit_date = models.DateField(default=timezone.localdate, db_index=True)
    reason = models.CharField(max_length=200)
    restock = models.BooleanField(default=True, help_text="Return goods to stock")
    subtotal = money_field()
    vat_amount = money_field()
    total = money_field()
    cost_total = money_field()
    journal_entry = models.ForeignKey("finance.JournalEntry", null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name="+")

    class Meta:
        ordering = ["-credit_date", "-id"]

    def __str__(self):
        return self.number


class CreditNoteLine(models.Model):
    credit_note = models.ForeignKey(CreditNote, on_delete=models.CASCADE, related_name="lines")
    invoice_line = models.ForeignKey(InvoiceLine, on_delete=models.PROTECT, related_name="credit_lines")
    product = models.ForeignKey("inventory.Product", on_delete=models.PROTECT, related_name="+")
    quantity = quantity_field()
    unit_price = money_field(help_text="Net unit price after discount")
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    line_subtotal = money_field()
    line_vat = money_field()
    line_total = money_field()
    unit_cost = money_field()

    class Meta:
        ordering = ["id"]
