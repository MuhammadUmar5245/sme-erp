"""Read-only reporting API for Power BI's Web connector: /api/v1/reports/<view>/.

Token authentication (Authorization: Token <key>), ?date_from / ?date_to filters on each view's date
column, page-number pagination (page, page_size up to 5000) and a `next` link that Power Query follows.
"""
import datetime

from rest_framework import serializers, viewsets
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import has_perms

from . import services
from .models import REPORTING_MODELS

POWERBI_PERMISSION = has_perms("reports.view_powerbi_api")


def _parse_date(value, name):
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise ValidationError({name: "Use the format YYYY-MM-DD."})


class ReportingViewSetBase(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [POWERBI_PERMISSION]
    filter_backends = []

    def get_queryset(self):
        qs = self.queryset.all()
        params = self.request.query_params
        date_field = self.queryset.model.date_field
        if date_field:
            if params.get("date_from"):
                qs = qs.filter(**{f"{date_field}__gte": _parse_date(params["date_from"], "date_from")})
            if params.get("date_to"):
                qs = qs.filter(**{f"{date_field}__lte": _parse_date(params["date_to"], "date_to")})
        return qs


def _make_viewset(slug, model):
    serializer = type(f"{model.__name__}Serializer", (serializers.ModelSerializer,),
                      {"Meta": type("Meta", (), {"model": model, "fields": "__all__"})})
    doc = f"Power BI dataset `{model._meta.db_table.replace(chr(34), '')}`."
    if model.date_field:
        doc += f" Filter with ?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD on `{model.date_field}`."
    return type(f"{model.__name__}ViewSet", (ReportingViewSetBase,),
                {"queryset": model.objects.all(), "serializer_class": serializer, "__doc__": doc})


REPORTING_VIEWSETS = {slug: _make_viewset(slug, model) for slug, model in REPORTING_MODELS.items()}


class KPIView(APIView):
    """Headline KPIs (same figures as the in-app dashboard)."""

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [has_perms("reports.view_dashboard")]

    def get(self, request):
        return Response(services.kpis())


class DatasetIndexView(APIView):
    """List of reporting datasets and their URLs (entry point for Power BI)."""

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [POWERBI_PERMISSION]

    def get(self, request):
        base = request.build_absolute_uri("/api/v1/reports/")
        return Response([{"name": slug, "url": f"{base}{slug}/", "date_field": model.date_field,
                          "view": model._meta.db_table.replace('"', "")} for slug, model in REPORTING_MODELS.items()])
