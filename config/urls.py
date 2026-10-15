from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from core.views import health

admin.site.site_header = "SME-ERP administration"
admin.site.site_title = "SME-ERP"

urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("api/v1/", include("config.api_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="swagger-ui"),
    path("accounts/", include("accounts.urls")),
    path("inventory/", include("inventory.urls")),
    path("purchasing/", include("purchasing.urls")),
    path("sales/", include("sales.urls")),
    path("crm/", include("crm.urls")),
    path("finance/", include("finance.urls")),
    path("hr/", include("hr.urls")),
    path("reports/", include("reports.urls")),
    path("integrations/", include("integrations.urls")),
    path("", include("core.urls")),
]
