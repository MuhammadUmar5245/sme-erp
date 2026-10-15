from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import has_perms
from inventory.models import Product
from inventory.services import InsufficientStock

from . import services
from .models import CreditNote, CreditNoteLine, Invoice, InvoiceLine, Payment, SalesOrder, SalesOrderLine

ERRORS = (services.SalesError, InsufficientStock)


def _raise(exc):
    raise serializers.ValidationError({"detail": str(exc)})


class SalesLineInputSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    unit_price = serializers.DecimalField(max_digits=14, decimal_places=3, required=False)
    discount_pct = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=0)
    vat_rate = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)


class SalesOrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesOrderLine
        fields = ["id", "product", "quantity", "unit_price", "discount_pct", "vat_rate"]


class SalesOrderSerializer(serializers.ModelSerializer):
    lines = SalesOrderLineSerializer(many=True, read_only=True)
    input_lines = SalesLineInputSerializer(many=True, write_only=True, source="lines_in")

    class Meta:
        model = SalesOrder
        fields = ["id", "number", "customer", "warehouse", "order_date", "delivery_date", "status", "notes",
                  "subtotal", "vat_amount", "total", "salesperson", "lines", "input_lines"]
        read_only_fields = ["number", "status", "subtotal", "vat_amount", "total", "salesperson"]

    def create(self, d):
        try:
            return services.create_sales_order(d["customer"], d["warehouse"], d["lines_in"],
                                               self.context["request"].user, d.get("order_date"),
                                               d.get("delivery_date"), d.get("notes", ""))
        except ERRORS as exc:
            _raise(exc)


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = ["id", "product", "description", "quantity", "unit_price", "discount_pct", "vat_rate",
                  "line_subtotal", "line_vat", "line_total"]


class InvoiceSerializer(serializers.ModelSerializer):
    lines = InvoiceLineSerializer(many=True, read_only=True)
    input_lines = SalesLineInputSerializer(many=True, write_only=True, source="lines_in")
    balance_due = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)

    class Meta:
        model = Invoice
        fields = ["id", "number", "customer", "warehouse", "sales_order", "invoice_date", "due_date", "status",
                  "source", "external_ref", "subtotal", "vat_amount", "total", "amount_paid", "amount_credited",
                  "balance_due", "notes", "lines", "input_lines"]
        read_only_fields = ["number", "sales_order", "due_date", "status", "source", "subtotal", "vat_amount", "total",
                            "amount_paid", "amount_credited"]

    def create(self, d):
        try:
            return services.create_invoice(d["customer"], d["warehouse"], d["lines_in"], self.context["request"].user,
                                           d.get("invoice_date"), external_ref=d.get("external_ref", ""),
                                           notes=d.get("notes", ""))
        except ERRORS as exc:
            _raise(exc)


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "number", "invoice", "customer", "payment_date", "amount", "method", "reference"]
        read_only_fields = ["number", "customer"]

    def create(self, d):
        try:
            return services.record_payment(d["invoice"], d["amount"], d.get("payment_date"), d.get("method", "BANK"),
                                           d.get("reference", ""), self.context["request"].user)
        except services.SalesError as exc:
            _raise(exc)


class CreditLineInputSerializer(serializers.Serializer):
    invoice_line = serializers.PrimaryKeyRelatedField(queryset=InvoiceLine.objects.all())
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)


class CreditNoteLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditNoteLine
        fields = ["invoice_line", "product", "quantity", "unit_price", "line_subtotal", "line_vat", "line_total"]


class CreditNoteSerializer(serializers.ModelSerializer):
    lines = CreditNoteLineSerializer(many=True, read_only=True)
    input_lines = CreditLineInputSerializer(many=True, write_only=True, source="lines_in")

    class Meta:
        model = CreditNote
        fields = ["id", "number", "invoice", "customer", "credit_date", "reason", "restock", "subtotal", "vat_amount",
                  "total", "lines", "input_lines"]
        read_only_fields = ["number", "customer", "subtotal", "vat_amount", "total"]

    def create(self, d):
        try:
            return services.create_credit_note(d["invoice"], d["lines_in"], d["reason"], d.get("credit_date"),
                                               d.get("restock", True), self.context["request"].user)
        except services.SalesError as exc:
            _raise(exc)


class SalesOrderViewSet(viewsets.ModelViewSet):
    queryset = SalesOrder.objects.select_related("customer").prefetch_related("lines")
    serializer_class = SalesOrderSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["status", "customer", "warehouse"]
    search_fields = ["number", "customer__name"]

    @action(detail=True, methods=["post"], permission_classes=[has_perms("sales.change_salesorder")])
    def confirm(self, request, pk=None):
        try:
            order = services.confirm_sales_order(self.get_object(), request.user)
        except services.SalesError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"], permission_classes=[has_perms("sales.add_invoice")])
    def invoice(self, request, pk=None):
        try:
            invoice = services.invoice_sales_order(self.get_object(), request.user)
        except ERRORS as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related("customer").prefetch_related("lines")
    serializer_class = InvoiceSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["status", "customer", "source", "warehouse"]
    search_fields = ["number", "customer__name", "external_ref"]
    ordering_fields = ["invoice_date", "total", "due_date"]


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("invoice")
    serializer_class = PaymentSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["invoice", "customer", "method"]


class CreditNoteViewSet(viewsets.ModelViewSet):
    queryset = CreditNote.objects.prefetch_related("lines")
    serializer_class = CreditNoteSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["invoice", "customer"]
