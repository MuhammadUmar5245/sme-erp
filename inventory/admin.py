from django.contrib import admin

from .models import Category, Product, StockMovement, Warehouse


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["code", "name"]
    search_fields = ["code", "name"]


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "city", "is_active"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["sku", "name", "category", "unit", "cost_price", "sale_price", "reorder_level", "is_active"]
    list_filter = ["category", "is_active", "unit"]
    search_fields = ["sku", "name", "barcode"]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    """Movements are created by services only; the admin is read-only to keep stock consistent."""

    list_display = ["movement_date", "product", "warehouse", "movement_type", "quantity", "reference_no"]
    list_filter = ["movement_type", "reference_type", "warehouse"]
    search_fields = ["product__sku", "reference_no"]
    date_hierarchy = "movement_date"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
