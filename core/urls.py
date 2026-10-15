from django.urls import path

from . import support, views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("support/", support.support, name="support"),
    path("support/feedback/", support.feedback_overview, name="feedback_overview"),
    path("support/feedback/<int:pk>/resolve/", support.feedback_resolve, name="feedback_resolve"),
]
