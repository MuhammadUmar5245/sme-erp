from django.urls import path

from . import views

app_name = "hr"

urlpatterns = [
    path("departments/", views.DepartmentListView.as_view(), name="department_list"),
    path("departments/new/", views.DepartmentCreateView.as_view(), name="department_create"),
    path("departments/<int:pk>/", views.DepartmentDetailView.as_view(), name="department_detail"),
    path("departments/<int:pk>/edit/", views.DepartmentUpdateView.as_view(), name="department_update"),
    path("employees/", views.EmployeeListView.as_view(), name="employee_list"),
    path("employees/new/", views.EmployeeCreateView.as_view(), name="employee_create"),
    path("employees/<int:pk>/", views.EmployeeDetailView.as_view(), name="employee_detail"),
    path("employees/<int:pk>/edit/", views.EmployeeUpdateView.as_view(), name="employee_update"),
    path("leave/", views.LeaveListView.as_view(), name="leave_list"),
    path("leave/new/", views.leave_create, name="leave_create"),
    path("leave/<int:pk>/", views.LeaveDetailView.as_view(), name="leave_detail"),
    path("leave/<int:pk>/approve/", views.leave_approve, name="leave_approve"),
    path("leave/<int:pk>/reject/", views.leave_reject, name="leave_reject"),
]
