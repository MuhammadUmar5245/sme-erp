from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services


@login_required
@permission_required("monitoring.view_requestmetric", raise_exception=True)
def dashboard(request):
    hours = int(request.GET.get("hours", 24)) if request.GET.get("hours", "24").isdigit() else 24
    hours = min(max(hours, 1), 24 * 30)
    return render(request, "monitoring/dashboard.html", {
        "title": "System monitoring", "m": services.summary(hours), "series": services.hourly_series(hours),
        "hours": hours, "periods": [(1, "1 hour"), (24, "24 hours"), (168, "7 days"), (720, "30 days")],
    })


class CanReadSystemMetrics(BasePermission):
    """Admins (monitoring permission) and the Power BI service account."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (
            user.has_perm("monitoring.view_requestmetric") or user.has_perm("reports.view_powerbi_api")))


class SystemMetricsView(APIView):
    """GET /api/v1/reports/system-metrics/?hours=24 - the monitoring page figures for Power BI."""

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [CanReadSystemMetrics]

    def get(self, request):
        raw = request.query_params.get("hours", "24")
        hours = min(max(int(raw), 1), 24 * 90) if raw.isdigit() else 24
        data = services.summary(hours)
        data["hourly"] = services.hourly_series(min(hours, 24 * 7))
        return Response(data)
