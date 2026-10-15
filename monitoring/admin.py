from django.contrib import admin

from .models import HealthProbe, RequestMetric


@admin.register(RequestMetric)
class RequestMetricAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "method", "endpoint", "status_code", "duration_ms", "user_id"]
    list_filter = ["method", "status_code", "is_api"]
    search_fields = ["endpoint", "view_name"]
    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(HealthProbe)
class HealthProbeAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "ok", "db_ms"]
    list_filter = ["ok"]

    def has_add_permission(self, request):
        return False
