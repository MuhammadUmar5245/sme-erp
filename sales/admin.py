from django.contrib import admin

from .models import CreditNote, CreditNoteLine, Invoice, InvoiceLine, Payment, SalesOrder, SalesOrderLine


class SOLineInline(admin.TabularInline):
    model = SalesOrderLine
    extra = 0


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ["number", "order_date", "customer", "total", "status"]
    list_filter = ["status", "warehouse"]
    search_fields = ["number", "customer__name"]
    inlines = [SOLineInline]
    readonly_fields = ["number", "subtotal", "vat_amount", "total"]


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    can_delete = False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """Posted invoices are read-only: corrections go through credit notes."""

    list_display = ["number", "invoice_date", "customer", "total", "amount_paid", "status", "source"]
    list_filter = ["status", "source", "warehouse"]
    search_fields = ["number", "customer__name", "external_ref"]
    date_hierarchy = "invoice_date"
    inlines = [InvoiceLineInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["number", "payment_date", "customer", "invoice", "amount", "method"]
    list_filter = ["method"]

    def has_add_permission(self, request):
        return False


class CreditNoteLineInline(admin.TabularInline):
    model = CreditNoteLine
    extra = 0


@admin.register(CreditNote)
class CreditNoteAdmin(admin.ModelAdmin):
    list_display = ["number", "credit_date", "customer", "invoice", "total"]
    inlines = [CreditNoteLineInline]

    def has_add_permission(self, request):
        return False
