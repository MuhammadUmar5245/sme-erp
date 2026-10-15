from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AuditLog, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ["email", "first_name", "last_name", "department", "is_active", "is_staff"]
    list_filter = ["is_active", "is_staff", "groups", "department"]
    search_fields = ["email", "first_name", "last_name"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("first_name", "last_name", "phone", "department")}),
        ("Access", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Read-only: audit records can never be edited or deleted through the UI."""

    list_display = ["timestamp", "user_email", "action", "model", "object_repr", "ip_address"]
    list_filter = ["action", "model"]
    search_fields = ["user_email", "object_repr", "object_id"]
    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
