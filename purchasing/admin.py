from django.contrib import admin

from .models import GoodsReceipt, GoodsReceiptLine, PurchaseOrder, PurchaseOrderLine, Supplier, SupplierBill, SupplierPayment


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "contact_person", "phone", "city", "payment_terms_days", "is_active"]
    search_fields = ["code", "name"]
    list_filter = ["city", "is_active"]


class POLineInline(admin.TabularInline):
    model = PurchaseOrderLine
    extra = 0


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ["number", "order_date", "supplier", "warehouse", "total", "status"]
    list_filter = ["status", "warehouse"]
    search_fields = ["number", "supplier__name"]
    inlines = [POLineInline]
    readonly_fields = ["number", "status", "subtotal", "vat_amount", "total", "approved_by", "approved_at"]


class GRNLineInline(admin.TabularInline):
    model = GoodsReceiptLine
    extra = 0


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ["number", "receipt_date", "purchase_order", "warehouse"]
    inlines = [GRNLineInline]

    def has_add_permission(self, request):
        return False


@admin.register(SupplierBill)
class SupplierBillAdmin(admin.ModelAdmin):
    list_display = ["number", "supplier_invoice_no", "supplier", "bill_date", "due_date", "total", "amount_paid", "status"]
    list_filter = ["status"]
    search_fields = ["number", "supplier_invoice_no", "supplier__name"]

    def has_add_permission(self, request):
        return False


@admin.register(SupplierPayment)
class SupplierPaymentAdmin(admin.ModelAdmin):
    list_display = ["number", "payment_date", "supplier", "bill", "amount", "method"]

    def has_add_permission(self, request):
        return False
