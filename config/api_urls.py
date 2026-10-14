"""REST API v1 routes (/api/v1/). Each module registers its viewsets on the shared router."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

urlpatterns = [
    path("", include(router.urls)),
]
