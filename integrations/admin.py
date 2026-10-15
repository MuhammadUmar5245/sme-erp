from django.contrib import admin

from .models import APIKey, IdempotencyRecord, ImportJob


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = ["pk", "entity", "original_filename", "status", "created_by", "created_at", "committed_at"]
    list_filter = ["entity", "status"]
    exclude = ["raw_rows", "results"]
    readonly_fields = ["entity", "original_filename", "status", "headers", "mapping", "summary", "dry_run",
                       "created_by", "committed_at"]


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    """Keys are created in the app (Data & integration > POS API keys) so the raw key can be shown once."""

    list_display = ["name", "prefix", "warehouse", "default_customer", "is_active", "last_used_at"]
    readonly_fields = ["prefix", "last_used_at"]

    def has_add_permission(self, request):
        return False


@admin.register(IdempotencyRecord)
class IdempotencyRecordAdmin(admin.ModelAdmin):
    list_display = ["key", "api_key", "status_code", "invoice", "created_at"]
    readonly_fields = ["api_key", "key", "request_hash", "status_code", "response", "invoice"]
