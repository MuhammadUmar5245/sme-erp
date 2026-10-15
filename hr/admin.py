from django.contrib import admin

from .models import Department, Employee, LeaveRequest


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active"]
    search_fields = ["code", "name"]


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ["employee_no", "full_name", "department", "job_title", "is_active"]
    list_filter = ["department", "is_active"]
    search_fields = ["employee_no", "first_name", "last_name"]


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ["employee", "leave_type", "start_date", "end_date", "days", "status"]
    list_filter = ["status", "leave_type"]
    readonly_fields = ["days", "decided_by", "decided_at"]
