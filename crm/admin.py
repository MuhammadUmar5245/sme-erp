from django.contrib import admin

from .models import Contact, Customer, Feedback, Interaction


class ContactInline(admin.TabularInline):
    model = Contact
    extra = 0


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "customer_type", "city", "phone", "credit_limit", "is_active"]
    list_filter = ["customer_type", "city", "is_active"]
    search_fields = ["code", "name", "phone", "email"]
    inlines = [ContactInline]


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ["interaction_date", "customer", "interaction_type", "subject", "status"]
    list_filter = ["interaction_type", "status"]
    search_fields = ["subject", "customer__name"]


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ["feedback_date", "customer", "score", "channel"]
    list_filter = ["score", "channel"]
    search_fields = ["customer__name", "comment"]


admin.site.register(Contact)
