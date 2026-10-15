from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import has_perms

from . import services
from .models import Department, Employee, LeaveRequest


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "code", "name", "is_active"]


class EmployeeSerializer(serializers.ModelSerializer):
    """Sensitive fields are write-only; reads return masked values."""

    national_id = serializers.CharField(write_only=True, required=False, allow_blank=True)
    bank_iban = serializers.CharField(write_only=True, required=False, allow_blank=True)
    national_id_masked = serializers.CharField(read_only=True)
    bank_iban_masked = serializers.CharField(read_only=True)

    class Meta:
        model = Employee
        fields = ["id", "employee_no", "first_name", "last_name", "department", "manager", "job_title", "hire_date",
                  "phone", "email", "city", "nationality", "basic_salary", "national_id", "bank_iban",
                  "national_id_masked", "bank_iban_masked", "annual_leave_days", "user", "is_active"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ["id", "employee", "leave_type", "start_date", "end_date", "days", "reason", "status", "decided_by",
                  "decided_at", "decision_note"]
        read_only_fields = ["days", "status", "decided_by", "decided_at", "decision_note"]

    def create(self, d):
        try:
            return services.submit_leave_request(d["employee"], d["leave_type"], d["start_date"], d["end_date"],
                                                 d.get("reason", ""), self.context["request"].user)
        except services.LeaveError as exc:
            raise serializers.ValidationError({"detail": str(exc)})


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.select_related("department")
    serializer_class = EmployeeSerializer
    filterset_fields = ["department", "is_active"]
    search_fields = ["employee_no", "first_name", "last_name"]


class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.select_related("employee")
    serializer_class = LeaveRequestSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["employee", "status", "leave_type"]

    def _decide(self, func):
        try:
            leave = func(self.get_object(), self.request.user, self.request.data.get("note", ""))
        except services.LeaveError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(leave).data)

    @action(detail=True, methods=["post"], permission_classes=[has_perms("hr.approve_leaverequest")])
    def approve(self, request, pk=None):
        return self._decide(services.approve_leave)

    @action(detail=True, methods=["post"], permission_classes=[has_perms("hr.approve_leaverequest")])
    def reject(self, request, pk=None):
        return self._decide(services.reject_leave)
