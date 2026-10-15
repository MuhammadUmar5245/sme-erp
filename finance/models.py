from django.conf import settings
from django.db import models
from django.db.models import Sum

from core.models import TimeStampedModel, money_field


class Account(TimeStampedModel):
    """Chart of accounts entry."""

    class Type(models.TextChoices):
        ASSET = "ASSET", "Asset"
        LIABILITY = "LIABILITY", "Liability"
        EQUITY = "EQUITY", "Equity"
        INCOME = "INCOME", "Income"
        EXPENSE = "EXPENSE", "Expense"

    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=10, choices=Type.choices)
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False, help_text="Used by automatic postings; cannot be deleted")
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} {self.name}"

    @property
    def normal_debit(self):
        return self.account_type in (self.Type.ASSET, self.Type.EXPENSE)


class JournalEntry(models.Model):
    class Source(models.TextChoices):
        INVOICE = "INV", "Sales invoice"
        PAYMENT = "PAY", "Customer payment"
        CREDIT_NOTE = "CN", "Credit note"
        GOODS_RECEIPT = "GRN", "Goods receipt"
        SUPPLIER_BILL = "BILL", "Supplier bill"
        SUPPLIER_PAYMENT = "SPAY", "Supplier payment"
        EXPENSE = "EXP", "Expense"
        STOCK_ADJUSTMENT = "ADJ", "Stock adjustment"
        OPENING = "OPEN", "Opening balance"
        MANUAL = "MAN", "Manual journal"

    number = models.CharField(max_length=30, unique=True)
    entry_date = models.DateField(db_index=True)
    description = models.CharField(max_length=255)
    source_type = models.CharField(max_length=5, choices=Source.choices, default=Source.MANUAL, db_index=True)
    source_id = models.BigIntegerField(null=True, blank=True)
    reference = models.CharField(max_length=60, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-entry_date", "-id"]
        verbose_name_plural = "journal entries"
        indexes = [models.Index(fields=["source_type", "source_id"])]

    def __str__(self):
        return f"{self.number} {self.description}"

    @property
    def total_debit(self):
        return self.lines.aggregate(t=Sum("debit"))["t"] or 0

    @property
    def total_credit(self):
        return self.lines.aggregate(t=Sum("credit"))["t"] or 0


class JournalLine(models.Model):
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="lines")
    debit = money_field()
    credit = money_field()
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(debit__gte=0) & models.Q(credit__gte=0), name="journal_line_non_negative"
            ),
            models.CheckConstraint(
                condition=~(models.Q(debit__gt=0) & models.Q(credit__gt=0)), name="journal_line_one_side"
            ),
        ]

    def __str__(self):
        return f"{self.account.code} Dr {self.debit} Cr {self.credit}"


class Expense(TimeStampedModel):
    class PaidFrom(models.TextChoices):
        CASH = "1000", "Cash on hand"
        BANK = "1010", "Bank"

    number = models.CharField(max_length=30, unique=True, editable=False)
    expense_date = models.DateField()
    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="expenses",
        limit_choices_to={"account_type": Account.Type.EXPENSE},
    )
    payee = models.CharField(max_length=120)
    description = models.CharField(max_length=200)
    amount = money_field(help_text="Net amount excluding VAT")
    vat_amount = money_field()
    total = money_field()
    paid_from = models.CharField(max_length=4, choices=PaidFrom.choices, default=PaidFrom.BANK)
    reference = models.CharField(max_length=60, blank=True)
    journal_entry = models.OneToOneField(JournalEntry, null=True, blank=True, on_delete=models.SET_NULL,
                                         related_name="expense")

    class Meta:
        ordering = ["-expense_date", "-id"]

    def __str__(self):
        return f"{self.number} {self.payee}"
