"""REST API v1 routes (/api/v1/)."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts import api as accounts_api

router = DefaultRouter()
router.register("accounts/users", accounts_api.UserViewSet, basename="user")
router.register("accounts/audit-logs", accounts_api.AuditLogViewSet, basename="auditlog")

urlpatterns = [
    path("auth/token/", accounts_api.ObtainTokenView.as_view(), name="api-token"),
    path("", include(router.urls)),
]
