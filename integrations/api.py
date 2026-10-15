from decimal import Decimal

from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from rest_framework import authentication, exceptions, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import APIKey


class APIKeyAuthentication(authentication.BaseAuthentication):
    """`X-API-Key: pos_...` header. request.auth becomes the APIKey; there is no user."""

    def authenticate(self, request):
        raw = request.headers.get("X-API-Key")
        if not raw:
            return None
        key = services.authenticate_api_key(raw)
        if key is None:
            raise exceptions.AuthenticationFailed("Invalid or revoked API key.")
        return AnonymousUser(), key

    def authenticate_header(self, request):
        return "X-API-Key"


class HasAPIKey(permissions.BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.auth, APIKey)


class POSLineSerializer(serializers.Serializer):
    sku = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))
    unit_price = serializers.DecimalField(max_digits=14, decimal_places=3, required=False)
    discount_pct = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)


class POSPaymentSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=["CASH", "CARD", "BANK", "CHEQUE"], default="CASH")
    amount = serializers.DecimalField(max_digits=14, decimal_places=3, required=False)


class POSSaleSerializer(serializers.Serializer):
    receipt_no = serializers.CharField(max_length=60)
    sale_date = serializers.DateField(required=False)
    warehouse = serializers.CharField(required=False, help_text="Warehouse code; defaults to the API key's")
    customer_code = serializers.CharField(required=False, help_text="Defaults to the API key's walk-in customer")
    lines = POSLineSerializer(many=True)
    payment = POSPaymentSerializer(required=False)


class POSSalesView(APIView):
    """POS integration: POST a completed sale; creates a tax invoice (stock OUT + journal) and its payment.

    Headers: `X-API-Key` (required) and `Idempotency-Key` (required, unique per sale). Re-sending the
    same request with the same Idempotency-Key returns the original invoice (header Idempotent-Replayed).
    """

    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasAPIKey]
    serializer_class = POSSaleSerializer

    def post(self, request):
        body = POSSaleSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        payload = {**request.data}
        try:
            code, data, replayed = services.process_pos_sale(request.auth, request.headers.get("Idempotency-Key", ""),
                                                             payload)
        except services.POSError as exc:
            return Response({"detail": str(exc)}, status=exc.status)
        response = Response(data, status=status.HTTP_200_OK if replayed else code)
        if replayed:
            response["Idempotent-Replayed"] = "true"
        return response


class ExportView(APIView):
    """GET /api/v1/integrations/export/<entity>/?format=csv|xlsx - master data export."""

    def get(self, request, entity):
        if entity not in services.EXPORTS:
            return Response({"detail": f"Unknown entity. Choose from {', '.join(services.EXPORTS)}."}, status=404)
        if not request.user.has_perm(services.EXPORT_PERMISSIONS[entity]):
            raise exceptions.PermissionDenied()
        fmt = request.query_params.get("format", "csv")
        if fmt == "xlsx":
            response = HttpResponse(services.export_xlsx(entity),
                                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        elif fmt == "csv":
            response = HttpResponse(services.export_csv(entity), content_type="text/csv")
        else:
            return Response({"detail": "format must be csv or xlsx"}, status=400)
        response["Content-Disposition"] = f'attachment; filename="{entity}.{fmt}"'
        return response

    def get_permissions(self):
        return [permissions.IsAuthenticated()]
