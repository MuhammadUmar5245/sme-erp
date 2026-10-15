from django.conf import settings
from django.db import models


class ImportJob(models.Model):
    """One legacy-data import: upload -> column mapping -> validation/cleansing -> dry run -> commit."""

    class Entity(models.TextChoices):
        CUSTOMERS = "customers", "Customers"
        SUPPLIERS = "suppliers", "Suppliers"
        PRODUCTS = "products", "Products"
        OPENING_STOCK = "opening_stock", "Opening stock"
        OPENING_BALANCES = "opening_balances", "Opening balances (GL)"

    class Status(models.TextChoices):
        UPLOADED = "UPLOADED", "Uploaded"
        MAPPED = "MAPPED", "Columns mapped"
        VALIDATED = "VALIDATED", "Validated"
        COMMITTED = "COMMITTED", "Committed"
        FAILED = "FAILED", "Failed"

    entity = models.CharField(max_length=20, choices=Entity.choices)
    original_filename = models.CharField(max_length=200)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.UPLOADED)
    headers = models.JSONField(default=list)
    raw_rows = models.JSONField(default=list, help_text="Rows as read from the file (list of dicts)")
    mapping = models.JSONField(default=dict, help_text="target field -> source column")
    results = models.JSONField(default=list, help_text="Per-row validation and cleansing results")
    summary = models.JSONField(default=dict)
    dry_run = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    committed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Import #{self.pk} {self.get_entity_display()} ({self.original_filename})"


class APIKey(models.Model):
    """API key for machine clients such as the point-of-sale system. Only a SHA-256 hash is stored."""

    name = models.CharField(max_length=100)
    prefix = models.CharField(max_length=12, unique=True, editable=False)
    key_hash = models.CharField(max_length=64, editable=False)
    is_active = models.BooleanField(default=True)
    warehouse = models.ForeignKey("inventory.Warehouse", on_delete=models.PROTECT, related_name="+",
                                  help_text="Stock is issued from this warehouse")
    default_customer = models.ForeignKey("crm.Customer", on_delete=models.PROTECT, related_name="+",
                                         help_text="Walk-in / cash customer used when the sale has no customer code")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "API key"

    def __str__(self):
        return f"{self.name} ({self.prefix}...)"


class IdempotencyRecord(models.Model):
    """Remembers the response for each (API key, Idempotency-Key) so retried POS requests never double-post."""

    api_key = models.ForeignKey(APIKey, on_delete=models.CASCADE, related_name="idempotency_records")
    key = models.CharField(max_length=100)
    request_hash = models.CharField(max_length=64)
    status_code = models.PositiveSmallIntegerField(default=0)
    response = models.JSONField(default=dict)
    invoice = models.ForeignKey("sales.Invoice", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["api_key", "key"], name="unique_idempotency_key_per_api_key")]

    def __str__(self):
        return f"{self.api_key.prefix}:{self.key}"
