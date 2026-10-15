from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import has_perms
from inventory.models import Product

from . import services
from .models import GoodsReceipt, GoodsReceiptLine, PurchaseOrder, PurchaseOrderLine, Supplier, SupplierBill, SupplierPayment


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "code", "name", "contact_person", "phone", "email", "city", "country", "address",
                  "vat_number", "payment_terms_days", "is_active"]


class POLineSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    unit_cost = serializers.DecimalField(max_digits=14, decimal_places=3, required=False)

    class Meta:
        model = PurchaseOrderLine
        fields = ["id", "product", "quantity", "unit_cost", "vat_rate", "received_quantity"]
        read_only_fields = ["received_quantity"]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    lines = POLineSerializer(many=True)

    class Meta:
        model = PurchaseOrder
        fields = ["id", "number", "supplier", "warehouse", "order_date", "expected_date", "status", "notes",
                  "subtotal", "vat_amount", "total", "approved_by", "approved_at", "lines"]
        read_only_fields = ["number", "status", "subtotal", "vat_amount", "total", "approved_by", "approved_at"]

    def create(self, d):
        try:
            return services.create_purchase_order(d["supplier"], d["warehouse"], d["lines"],
                                                  self.context["request"].user, d.get("order_date"),
                                                  d.get("expected_date"), d.get("notes", ""))
        except services.PurchasingError as exc:
            raise serializers.ValidationError({"detail": str(exc)})

    def update(self, order, d):
        try:
            return services.update_purchase_order(order, d.get("supplier", order.supplier),
                                                  d.get("warehouse", order.warehouse),
                                                  d.get("lines") or [{"product": l.product, "quantity": l.quantity,
                                                                       "unit_cost": l.unit_cost, "vat_rate": l.vat_rate}
                                                                      for l in order.lines.all()],
                                                  d.get("expected_date", order.expected_date), d.get("notes", order.notes))
        except services.PurchasingError as exc:
            raise serializers.ValidationError({"detail": str(exc)})


class GRNLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoodsReceiptLine
        fields = ["po_line", "product", "quantity", "unit_cost"]


class GoodsReceiptSerializer(serializers.ModelSerializer):
    lines = GRNLineSerializer(many=True, read_only=True)

    class Meta:
        model = GoodsReceipt
        fields = ["id", "number", "purchase_order", "warehouse", "receipt_date", "notes", "lines"]


class SupplierBillSerializer(serializers.ModelSerializer):
    balance_due = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)

    class Meta:
        model = SupplierBill
        fields = ["id", "number", "supplier_invoice_no", "supplier", "purchase_order", "bill_date", "due_date",
                  "subtotal", "vat_amount", "total", "amount_paid", "balance_due", "status", "journal_entry"]
        read_only_fields = fields


class SupplierPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierPayment
        fields = ["id", "number", "bill", "supplier", "payment_date", "amount", "method", "reference"]
        read_only_fields = ["number", "supplier"]

    def create(self, d):
        try:
            return services.pay_supplier_bill(d["bill"], d["amount"], d.get("payment_date"), d.get("method", "BANK"),
                                              d.get("reference", ""), self.context["request"].user)
        except services.PurchasingError as exc:
            raise serializers.ValidationError({"detail": str(exc)})


class ReceiveSerializer(serializers.Serializer):
    quantities = serializers.DictField(child=serializers.DecimalField(max_digits=12, decimal_places=3), required=False,
                                       help_text="{po_line_id: quantity}; omit to receive everything outstanding")
    receipt_date = serializers.DateField(required=False)


class BillRequestSerializer(serializers.Serializer):
    supplier_invoice_no = serializers.CharField(max_length=40)
    bill_date = serializers.DateField(required=False)


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    search_fields = ["code", "name"]
    filterset_fields = ["city", "is_active"]


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.select_related("supplier").prefetch_related("lines")
    serializer_class = PurchaseOrderSerializer
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    filterset_fields = ["status", "supplier", "warehouse"]
    search_fields = ["number", "supplier__name"]

    def _run(self, func, *args, **kwargs):
        try:
            result = func(*args, user=self.request.user, **kwargs)
        except services.PurchasingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return result

    @action(detail=True, methods=["post"], permission_classes=[has_perms("purchasing.approve_purchaseorder")])
    def approve(self, request, pk=None):
        result = self._run(services.approve_purchase_order, self.get_object())
        return result if isinstance(result, Response) else Response(self.get_serializer(result).data)

    @action(detail=True, methods=["post"], serializer_class=ReceiveSerializer,
            permission_classes=[has_perms("purchasing.add_goodsreceipt")])
    def receive(self, request, pk=None):
        body = ReceiveSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        result = self._run(services.receive_goods, self.get_object(), body.validated_data.get("quantities"),
                           receipt_date=body.validated_data.get("receipt_date"))
        if isinstance(result, Response):
            return result
        return Response(GoodsReceiptSerializer(result).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], serializer_class=BillRequestSerializer,
            permission_classes=[has_perms("purchasing.add_supplierbill")])
    def bill(self, request, pk=None):
        body = BillRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        result = self._run(services.create_bill_from_po, self.get_object(), body.validated_data["supplier_invoice_no"],
                           body.validated_data.get("bill_date"))
        if isinstance(result, Response):
            return result
        return Response(SupplierBillSerializer(result).data, status=status.HTTP_201_CREATED)


class GoodsReceiptViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GoodsReceipt.objects.prefetch_related("lines")
    serializer_class = GoodsReceiptSerializer
    filterset_fields = ["purchase_order", "warehouse"]


class SupplierBillViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SupplierBill.objects.select_related("supplier")
    serializer_class = SupplierBillSerializer
    filterset_fields = ["status", "supplier"]
    search_fields = ["number", "supplier_invoice_no"]


class SupplierPaymentViewSet(viewsets.ModelViewSet):
    queryset = SupplierPayment.objects.select_related("bill")
    serializer_class = SupplierPaymentSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["bill", "supplier", "method"]
