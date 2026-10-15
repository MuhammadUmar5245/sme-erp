from django.contrib import admin

from .models import FeasibilityStudy


@admin.register(FeasibilityStudy)
class FeasibilityStudyAdmin(admin.ModelAdmin):
    list_display = ["name", "created_by", "created_at"]
    readonly_fields = ["results"]
