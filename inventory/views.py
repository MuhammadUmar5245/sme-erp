import django_filters
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.shortcuts import redirect, render

from core.crud import ERPCreateView, ERPDeleteView, ERPDetailView, ERPListView, ERPUpdateView

from . import services
from .forms import CategoryForm, ProductForm, StockOperationForm, WarehouseForm
from .models import Category, Product, StockMovement, Warehouse

NS = "inventory"


class ProductFilter(django_filters.FilterSet):
    category = django_filters.ModelChoiceFilter(queryset=Category.objects.all())
    is_active = django_filters.BooleanFilter(label="Active")

    class Meta:
        model = Product
        fields = ["category", "unit", "is_active"]


class ProductListView(ERPListView):
    model = Product
    url_namespace, url_base = NS, "product"
    columns = [("sku", "SKU"), ("name", "Name"), ("category", "Category"), ("unit", "Unit"),
               ("cost_price", "Cost"), ("sale_price", "Price"), ("on_hand_qty", "On hand"),
               ("reorder_level", "Reorder at"), ("is_active", "Active")]
    search_fields = ["sku", "name", "barcode"]
    filterset_class = ProductFilter

    def get_queryset(self):
        return services.products_with_stock(queryset=super().get_queryset())


class ProductDetailView(ERPDetailView):
    model = Product
    url_namespace, url_base = NS, "product"
    template_name = "inventory/product_detail.html"
    fields = [("sku", "SKU"), ("name", "Name"), ("category", "Category"), ("unit", "Unit"), ("barcode", "Barcode"),
              ("cost_price", "Average cost (OMR)"), ("sale_price", "Sale price excl. VAT (OMR)"),
              ("vat_rate", "VAT %"), ("margin_pct", "Margin %"), ("reorder_level", "Reorder level"),
              ("reorder_quantity", "Reorder quantity"), ("is_active", "Active")]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        matrix = services.stock_matrix([self.object]).get(self.object.pk, {})
        ctx["stock_by_warehouse"] = [(wh, matrix.get(wh.pk, 0)) for wh in Warehouse.objects.all()]
        ctx["movements"] = self.object.movements.select_related("warehouse")[:20]
        return ctx


class ProductCreateView(ERPCreateView):
    model = Product
    form_class = ProductForm
    url_namespace, url_base = NS, "product"


class ProductUpdateView(ERPUpdateView):
    model = Product
    form_class = ProductForm
    url_namespace, url_base = NS, "product"


class ProductDeleteView(ERPDeleteView):
    model = Product
    url_namespace, url_base = NS, "product"


class CategoryListView(ERPListView):
    model = Category
    url_namespace, url_base = NS, "category"
    columns = [("code", "Code"), ("name", "Name"), ("description", "Description")]
    search_fields = ["code", "name"]


class CategoryDetailView(ERPDetailView):
    model = Category
    url_namespace, url_base = NS, "category"
    fields = [("code", "Code"), ("name", "Name"), ("description", "Description")]


class CategoryCreateView(ERPCreateView):
    model = Category
    form_class = CategoryForm
    url_namespace, url_base = NS, "category"


class CategoryUpdateView(ERPUpdateView):
    model = Category
    form_class = CategoryForm
    url_namespace, url_base = NS, "category"


class WarehouseListView(ERPListView):
    model = Warehouse
    url_namespace, url_base = NS, "warehouse"
    columns = [("code", "Code"), ("name", "Name"), ("city", "City"), ("is_active", "Active")]
    search_fields = ["code", "name", "city"]


class WarehouseDetailView(ERPDetailView):
    model = Warehouse
    url_namespace, url_base = NS, "warehouse"
    fields = [("code", "Code"), ("name", "Name"), ("city", "City"), ("address", "Address"), ("is_active", "Active")]


class WarehouseCreateView(ERPCreateView):
    model = Warehouse
    form_class = WarehouseForm
    url_namespace, url_base = NS, "warehouse"


class WarehouseUpdateView(ERPUpdateView):
    model = Warehouse
    form_class = WarehouseForm
    url_namespace, url_base = NS, "warehouse"


class MovementFilter(django_filters.FilterSet):
    movement_type = django_filters.ChoiceFilter(choices=StockMovement.Type.choices, label="Type")
    warehouse = django_filters.ModelChoiceFilter(queryset=Warehouse.objects.all())
    reference_type = django_filters.ChoiceFilter(choices=StockMovement.Reference.choices, label="Source")
    date_from = django_filters.DateFilter(field_name="movement_date", lookup_expr="date__gte", label="From")
    date_to = django_filters.DateFilter(field_name="movement_date", lookup_expr="date__lte", label="To")

    class Meta:
        model = StockMovement
        fields = ["movement_type", "warehouse", "reference_type"]


class MovementListView(ERPListView):
    model = StockMovement
    title = "Stock movements"
    url_namespace, url_base = NS, "movement"
    columns = [("movement_date", "Date"), ("product.sku", "SKU"), ("product.name", "Product"),
               ("warehouse.code", "Warehouse"), ("movement_type", "Type"), ("quantity", "Qty"),
               ("unit_cost", "Unit cost"), ("reference_type", "Source"), ("reference_no", "Reference")]
    search_fields = ["product__sku", "product__name", "reference_no"]
    filterset_class = MovementFilter
    paginate_by = 50

    def get_queryset(self):
        return super().get_queryset().select_related("product", "warehouse")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.user.has_perm("inventory.add_stockmovement"):
            from django.urls import reverse

            ctx["create_url"] = reverse("inventory:stock_operation")
        return ctx


@login_required
@permission_required("inventory.view_stockmovement", raise_exception=True)
def stock_levels(request):
    """Stock on hand per product per warehouse (computed from movements)."""
    warehouses = list(Warehouse.objects.filter(is_active=True))
    products = services.products_with_stock(queryset=Product.objects.filter(is_active=True))
    query = request.GET.get("q", "").strip()
    if query:
        products = products.filter(name__icontains=query) | products.filter(sku__icontains=query)
    if request.GET.get("low"):
        from django.db.models import F

        products = products.filter(on_hand_qty__lte=F("reorder_level"))
    page = Paginator(products.order_by("sku"), 50).get_page(request.GET.get("page"))
    matrix = services.stock_matrix(list(page.object_list))
    rows = [{"product": p, "cells": [matrix.get(p.pk, {}).get(w.pk, 0) for w in warehouses],
             "low": p.on_hand_qty <= p.reorder_level} for p in page.object_list]
    return render(request, "inventory/stock_levels.html", {
        "title": "Stock levels", "warehouses": warehouses, "rows": rows, "page_obj": page, "query": query,
        "inventory_value": services.inventory_value(), "low": request.GET.get("low"),
    })


@login_required
@permission_required("inventory.add_stockmovement", raise_exception=True)
def stock_operation(request):
    """Manual stock in / adjustment / transfer."""
    form = StockOperationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            if d["operation"] == "IN":
                services.receive_stock(d["product"], d["warehouse"], d["quantity"],
                                       d["unit_cost"] if d["unit_cost"] is not None else d["product"].cost_price,
                                       user=request.user, note=d["note"])
            elif d["operation"] == "ADJUST":
                services.adjust_stock(d["product"], d["warehouse"], d["quantity"], d["note"], user=request.user)
            else:
                services.transfer_stock(d["product"], d["warehouse"], d["to_warehouse"], d["quantity"],
                                        user=request.user, note=d["note"])
        except (services.InsufficientStock, ValueError) as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, "Stock movement recorded.")
            return redirect("inventory:movement_list")
    return render(request, "core/generic_form.html", {"form": form, "title": "Record stock movement",
                                                      "submit_label": "Record"})
