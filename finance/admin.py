from django.contrib import admin

from .models import Account, Expense, JournalEntry, JournalLine


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "account_type", "is_system", "is_active"]
    list_filter = ["account_type", "is_active"]
    search_fields = ["code", "name"]


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 0
    can_delete = False
    readonly_fields = ["account", "debit", "credit", "description"]


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    """Posted entries are immutable (corrections are made with reversing entries)."""

    list_display = ["number", "entry_date", "description", "source_type", "reference"]
    list_filter = ["source_type"]
    search_fields = ["number", "description", "reference"]
    date_hierarchy = "entry_date"
    inlines = [JournalLineInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["number", "expense_date", "account", "payee", "amount", "vat_amount", "total"]
    list_filter = ["account", "paid_from"]
    search_fields = ["number", "payee", "description"]
    readonly_fields = ["journal_entry"]

    def has_add_permission(self, request):
        return False
