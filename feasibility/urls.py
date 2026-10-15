from django.urls import path

from . import views

app_name = "feasibility"

urlpatterns = [
    path("", views.calculator, name="calculator"),
    path("pdf/", views.export_pdf, name="pdf"),
    path("save/", views.save_study, name="save"),
    path("studies/<int:pk>/", views.open_study, name="study"),
]
