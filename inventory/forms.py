from django import forms

from core.forms import BootstrapForm, BootstrapModelForm

from .models import Category, Product, Warehouse


class CategoryForm(BootstrapModelForm):
    class Meta:
        model = Category
        fields = ["code", "name", "description"]


class WarehouseForm(BootstrapModelForm):
    class Meta:
        model = Warehouse
        fields = ["code", "name", "city", "address", "is_active"]


class ProductForm(BootstrapModelForm):
    class Meta:
        model = Product
        fields = ["sku", "name", "category", "unit", "barcode", "cost_price", "sale_price", "vat_rate",
                  "reorder_level", "reorder_quantity", "is_active", "description"]

    def clean(self):
        data = super().clean()
        if data.get("sale_price") is not None and data["sale_price"] < 0:
            self.add_error("sale_price", "Price cannot be negative.")
        return data


class StockOperationForm(BootstrapForm):
    OPERATIONS = [("IN", "Stock in (receipt)"), ("ADJUST", "Adjustment (+/-)"), ("TRANSFER", "Transfer")]

    operation = forms.ChoiceField(choices=OPERATIONS)
    product = forms.ModelChoiceField(queryset=Product.objects.filter(is_active=True))
    warehouse = forms.ModelChoiceField(queryset=Warehouse.objects.filter(is_active=True))
    to_warehouse = forms.ModelChoiceField(queryset=Warehouse.objects.filter(is_active=True), required=False,
                                          help_text="Only for transfers")
    quantity = forms.DecimalField(max_digits=12, decimal_places=3, help_text="Negative allowed for adjustments")
    unit_cost = forms.DecimalField(max_digits=14, decimal_places=3, required=False,
                                   help_text="Stock in only; defaults to the product cost")
    note = forms.CharField(max_length=200, required=False)

    def clean(self):
        data = super().clean()
        op, qty = data.get("operation"), data.get("quantity")
        if qty is not None:
            if op in ("IN", "TRANSFER") and qty <= 0:
                self.add_error("quantity", "Quantity must be positive.")
            if op == "ADJUST" and qty == 0:
                self.add_error("quantity", "Adjustment cannot be zero.")
        if op == "TRANSFER" and not data.get("to_warehouse"):
            self.add_error("to_warehouse", "Choose the destination warehouse.")
        if op == "ADJUST" and not data.get("note"):
            self.add_error("note", "Give a reason for the adjustment.")
        return data
