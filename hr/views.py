import django_filters
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.crud import ERPCreateView, ERPDetailView, ERPListView, ERPUpdateView
from core.forms import BootstrapForm, BootstrapModelForm

from . import services
from .models import Department, Employee, LeaveRequest

NS = "hr"


class DepartmentForm(BootstrapModelForm):
    class Meta:
        model = Department
        fields = ["code", "name", "is_active"]


class EmployeeForm(BootstrapModelForm):
    class Meta:
        model = Employee
        fields = ["employee_no", "first_name", "last_name", "department", "manager", "job_title", "hire_date",
                  "phone", "email", "city", "nationality", "basic_salary", "national_id", "bank_iban",
                  "annual_leave_days", "user", "is_active"]
        widgets = {"national_id": forms.TextInput(), "bank_iban": forms.TextInput()}


class DepartmentListView(ERPListView):
    model = Department
    url_namespace, url_base = NS, "department"
    columns = [("code", "Code"), ("name", "Name"), ("is_active", "Active")]
    search_fields = ["code", "name"]


class DepartmentDetailView(ERPDetailView):
    model = Department
    url_namespace, url_base = NS, "department"
    fields = [("code", "Code"), ("name", "Name"), ("is_active", "Active")]


class DepartmentCreateView(ERPCreateView):
    model = Department
    form_class = DepartmentForm
    url_namespace, url_base = NS, "department"


class DepartmentUpdateView(ERPUpdateView):
    model = Department
    form_class = DepartmentForm
    url_namespace, url_base = NS, "department"


class EmployeeFilter(django_filters.FilterSet):
    department = django_filters.ModelChoiceFilter(queryset=Department.objects.all())
    is_active = django_filters.BooleanFilter(label="Active")

    class Meta:
        model = Employee
        fields = ["department", "is_active"]


class EmployeeListView(ERPListView):
    model = Employee
    url_namespace, url_base = NS, "employee"
    columns = [("employee_no", "No."), ("full_name", "Name"), ("department", "Department"),
               ("job_title", "Job title"), ("city", "City"), ("hire_date", "Hired"), ("is_active", "Active")]
    search_fields = ["employee_no", "first_name", "last_name", "job_title"]
    filterset_class = EmployeeFilter

    def get_queryset(self):
        return super().get_queryset().select_related("department")


class EmployeeDetailView(ERPDetailView):
    model = Employee
    url_namespace, url_base = NS, "employee"
    template_name = "hr/employee_detail.html"
    fields = [("employee_no", "Employee no."), ("full_name", "Name"), ("department", "Department"),
              ("manager", "Manager"), ("job_title", "Job title"), ("hire_date", "Hire date"), ("phone", "Phone"),
              ("email", "Email"), ("city", "City"), ("nationality", "Nationality"), ("basic_salary", "Basic salary"),
              ("national_id_masked", "Civil ID (masked)"), ("bank_iban_masked", "IBAN (masked)"),
              ("annual_leave_days", "Annual leave entitlement"), ("user", "System user")]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["leave_balance"] = services.leave_balance(self.object)
        ctx["leave_requests"] = self.object.leave_requests.all()[:10]
        return ctx


class EmployeeCreateView(ERPCreateView):
    model = Employee
    form_class = EmployeeForm
    url_namespace, url_base = NS, "employee"


class EmployeeUpdateView(ERPUpdateView):
    model = Employee
    form_class = EmployeeForm
    url_namespace, url_base = NS, "employee"


class LeaveFilter(django_filters.FilterSet):
    employee = django_filters.ModelChoiceFilter(queryset=Employee.objects.all())

    class Meta:
        model = LeaveRequest
        fields = ["status", "leave_type", "employee"]


class LeaveListView(ERPListView):
    model = LeaveRequest
    title = "Leave requests"
    url_namespace, url_base = NS, "leave"
    columns = [("employee.full_name", "Employee"), ("leave_type", "Type"), ("start_date", "From"),
               ("end_date", "To"), ("days", "Days"), ("status", "Status"), ("decided_by", "Decided by")]
    search_fields = ["employee__first_name", "employee__last_name", "reason"]
    filterset_class = LeaveFilter

    def get_queryset(self):
        return super().get_queryset().select_related("employee", "decided_by")


class LeaveDetailView(ERPDetailView):
    model = LeaveRequest
    url_namespace, url_base = NS, "leave"
    template_name = "hr/leave_detail.html"
    fields = [("employee", "Employee"), ("leave_type", "Type"), ("start_date", "From"), ("end_date", "To"),
              ("days", "Working days"), ("reason", "Reason"), ("status", "Status"), ("decided_by", "Decided by"),
              ("decided_at", "Decided at"), ("decision_note", "Decision note")]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.pop("update_url", None)
        ctx["balance"] = services.leave_balance(self.object.employee, self.object.start_date.year)
        return ctx


class LeaveForm(BootstrapForm):
    employee = forms.ModelChoiceField(queryset=Employee.objects.filter(is_active=True))
    leave_type = forms.ChoiceField(choices=LeaveRequest.Type.choices)
    start_date = forms.DateField(widget=forms.DateInput)
    end_date = forms.DateField(widget=forms.DateInput)
    reason = forms.CharField(max_length=200, required=False)


@login_required
@permission_required("hr.add_leaverequest", raise_exception=True)
def leave_create(request):
    initial = {}
    employee = getattr(request.user, "employee", None)
    if employee:
        initial["employee"] = employee.pk
    form = LeaveForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            leave = services.submit_leave_request(d["employee"], d["leave_type"], d["start_date"], d["end_date"],
                                                  d["reason"], request.user)
        except services.LeaveError as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, f"Leave request submitted ({leave.days} working days).")
            return redirect("hr:leave_detail", pk=leave.pk)
    return render(request, "core/generic_form.html", {"form": form, "title": "New leave request",
                                                      "submit_label": "Submit request"})


def _decide(request, pk, func, success):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    try:
        func(leave, request.user, request.POST.get("note", "")[:200])
    except services.LeaveError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, success)
    return redirect("hr:leave_detail", pk=pk)


@login_required
@permission_required("hr.approve_leaverequest", raise_exception=True)
@require_POST
def leave_approve(request, pk):
    return _decide(request, pk, services.approve_leave, "Leave approved.")


@login_required
@permission_required("hr.approve_leaverequest", raise_exception=True)
@require_POST
def leave_reject(request, pk):
    return _decide(request, pk, services.reject_leave, "Leave rejected.")
