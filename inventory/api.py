from django.db.models import F
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import has_perms

from . import services
from .models import Category, Product, StockMovement, Warehouse


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "code", "name", "description"]


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ["id", "code", "name", "city", "address", "is_active"]


class ProductSerializer(serializers.ModelSerializer):
    on_hand = serializers.DecimalField(source="on_hand_qty", max_digits=14, decimal_places=3, read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = ["id", "sku", "name", "category", "category_name", "unit", "barcode", "cost_price", "sale_price",
                  "vat_rate", "reorder_level", "reorder_quantity", "is_active", "on_hand"]


class StockMovementSerializer(serializers.ModelSerializer):
    to_warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.all(), write_only=True,
                                                      required=False)

    class Meta:
        model = StockMovement
        fields = ["id", "product", "warehouse", "to_warehouse", "movement_type", "quantity", "unit_cost",
                  "reference_type", "reference_no", "movement_date", "note"]
        read_only_fields = ["reference_type", "reference_no", "movement_date"]

    def create(self, data):
        user = self.context["request"].user
        kind = data["movement_type"]
        try:
            if kind == StockMovement.Type.IN:
                return services.receive_stock(data["product"], data["warehouse"], data["quantity"],
                                              data.get("unit_cost") or data["product"].cost_price, user=user,
                                              note=data.get("note", ""))
            if kind == StockMovement.Type.OUT:
                return services.issue_stock(data["product"], data["warehouse"], data["quantity"], user=user,
                                            note=data.get("note", ""))
            if kind == StockMovement.Type.ADJUST:
                return services.adjust_stock(data["product"], data["warehouse"], data["quantity"],
                                             data.get("note") or "API adjustment", user=user)
            if "to_warehouse" not in data:
                raise serializers.ValidationError({"to_warehouse": "Required for transfers."})
            return services.transfer_stock(data["product"], data["warehouse"], data["to_warehouse"],
                                           data["quantity"], user=user, note=data.get("note", ""))[1]
        except services.InsufficientStock as exc:
            raise serializers.ValidationError({"quantity": str(exc)})
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)})


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ["code", "name"]


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    search_fields = ["code", "name", "city"]


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    search_fields = ["sku", "name", "barcode"]
    filterset_fields = ["category", "is_active", "unit"]
    ordering_fields = ["sku", "name", "sale_price", "on_hand_qty"]

    def get_queryset(self):
        return services.products_with_stock().order_by("sku")

    @action(detail=False, url_path="low-stock")
    def low_stock(self, request):
        qs = self.get_queryset().filter(is_active=True, on_hand_qty__lte=F("reorder_level"))
        return Response(self.get_serializer(qs, many=True).data)


class StockMovementViewSet(viewsets.ModelViewSet):
    queryset = StockMovement.objects.select_related("product", "warehouse")
    serializer_class = StockMovementSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["product", "warehouse", "movement_type", "reference_type"]
    search_fields = ["product__sku", "reference_no"]

    @action(detail=False, url_path="stock-levels", permission_classes=[has_perms("inventory.view_stockmovement")])
    def stock_levels(self, request):
        rows = [
            {"product_id": pid, "warehouse_id": wid, "on_hand": str(qty)}
            for pid, by_wh in services.stock_matrix().items() for wid, qty in by_wh.items()
        ]
        return Response(rows, status=status.HTTP_200_OK)
