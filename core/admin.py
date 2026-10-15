from django.contrib import admin

from .models import Sequence, SystemFeedback


@admin.register(SystemFeedback)
class SystemFeedbackAdmin(admin.ModelAdmin):
    list_display = ["created_at", "user", "kind", "area", "rating", "status"]
    list_filter = ["kind", "area", "status"]
    search_fields = ["comment"]


@admin.register(Sequence)
class SequenceAdmin(admin.ModelAdmin):
    list_display = ["name", "last_value"]
    readonly_fields = ["name", "last_value"]
