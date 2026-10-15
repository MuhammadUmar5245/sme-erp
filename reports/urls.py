from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/data/", views.dashboard_data, name="dashboard_data"),
    path("builder/", views.report_builder, name="builder"),
    path("builder/export/<str:fmt>/", views.report_export, name="export"),
]
