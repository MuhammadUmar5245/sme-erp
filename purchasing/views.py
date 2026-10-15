import django_filters
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.crud import ERPCreateView, ERPDetailView, ERPListView, ERPUpdateView
from core.documents import LineForm, document_view, line_formset
from core.forms import BootstrapForm, BootstrapModelForm
from inventory.models import Product, Warehouse

from . import services
from .models import GoodsReceipt, PurchaseOrder, Supplier, SupplierBill, SupplierPayment

NS = "purchasing"


# ---- Suppliers -------------------------------------------------------------------------------


class SupplierForm(BootstrapModelForm):
    class Meta:
        model = Supplier
        fields = ["code", "name", "contact_person", "phone", "email", "city", "country", "address", "vat_number",
                  "payment_terms_days", "is_active"]


class SupplierListView(ERPListView):
    model = Supplier
    url_namespace, url_base = NS, "supplier"
    columns = [("code", "Code"), ("name", "Name"), ("contact_person", "Contact"), ("phone", "Phone"),
               ("city", "City"), ("payment_terms_days", "Terms (days)"), ("is_active", "Active")]
    search_fields = ["code", "name", "contact_person", "phone"]


class SupplierDetailView(ERPDetailView):
    model = Supplier
    url_namespace, url_base = NS, "supplier"
    template_name = "purchasing/supplier_detail.html"
    fields = [("code", "Code"), ("name", "Name"), ("contact_person", "Contact"), ("phone", "Phone"),
              ("email", "Email"), ("city", "City"), ("country", "Country"), ("vat_number", "VAT number"),
              ("payment_terms_days", "Payment terms (days)"), ("is_active", "Active")]


class SupplierCreateView(ERPCreateView):
    model = Supplier
    form_class = SupplierForm
    url_namespace, url_base = NS, "supplier"


class SupplierUpdateView(ERPUpdateView):
    model = Supplier
    form_class = SupplierForm
    url_namespace, url_base = NS, "supplier"


# ---- Purchase orders -------------------------------------------------------------------------


class POFilter(django_filters.FilterSet):
    supplier = django_filters.ModelChoiceFilter(queryset=Supplier.objects.all())
    date_from = django_filters.DateFilter(field_name="order_date", lookup_expr="gte", label="From")
    date_to = django_filters.DateFilter(field_name="order_date", lookup_expr="lte", label="To")

    class Meta:
        model = PurchaseOrder
        fields = ["status", "supplier", "warehouse"]


class POListView(ERPListView):
    model = PurchaseOrder
    title = "Purchase orders"
    url_namespace, url_base = NS, "po"
    columns = [("number", "Number"), ("order_date", "Date"), ("supplier.name", "Supplier"),
               ("warehouse.code", "Warehouse"), ("total", "Total"), ("status", "Status")]
    search_fields = ["number", "supplier__name"]
    filterset_class = POFilter

    def get_queryset(self):
        return super().get_queryset().select_related("supplier", "warehouse")


class PODetailView(ERPDetailView):
    model = PurchaseOrder
    url_namespace, url_base = NS, "po"
    template_name = "purchasing/po_detail.html"
    fields = [("number", "Number"), ("supplier", "Supplier"), ("warehouse", "Deliver to"),
              ("order_date", "Order date"), ("expected_date", "Expected"), ("status", "Status"),
              ("approved_by", "Approved by"), ("notes", "Notes")]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.object.status != PurchaseOrder.Status.DRAFT:
            ctx.pop("update_url", None)
        ctx.pop("delete_url", None)
        return ctx


class POHeaderForm(BootstrapForm):
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.filter(is_active=True))
    warehouse = forms.ModelChoiceField(queryset=Warehouse.objects.filter(is_active=True))
    expected_date = forms.DateField(required=False, widget=forms.DateInput)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))


class POLineForm(LineForm):
    product = forms.ModelChoiceField(queryset=Product.objects.filter(is_active=True))
    quantity = forms.DecimalField(max_digits=12, decimal_places=3, min_value=0.001)
    unit_cost = forms.DecimalField(max_digits=14, decimal_places=3, required=False, min_value=0,
                                   help_text="Blank = product cost")
    vat_rate = forms.DecimalField(max_digits=5, decimal_places=2, required=False, label="VAT %")


@login_required
@permission_required("purchasing.add_purchaseorder", raise_exception=True)
def po_create(request):
    def save(h, lines):
        order = services.create_purchase_order(h["supplier"], h["warehouse"], lines, request.user,
                                               expected_date=h["expected_date"], notes=h["notes"])
        return reverse("purchasing:po_detail", args=[order.pk])

    return document_view(request, header_form=POHeaderForm, formset_class=line_formset(POLineForm), save=save,
                         title="New purchase order", list_url=reverse("purchasing:po_list"),
                         success_message="Purchase order created as draft.", errors=(services.PurchasingError,))


@login_required
@permission_required("purchasing.change_purchaseorder", raise_exception=True)
def po_update(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    if order.status != PurchaseOrder.Status.DRAFT:
        messages.error(request, "Only draft purchase orders can be edited.")
        return redirect("purchasing:po_detail", pk=pk)

    def save(h, lines):
        services.update_purchase_order(order, h["supplier"], h["warehouse"], lines, h["expected_date"], h["notes"])
        return reverse("purchasing:po_detail", args=[order.pk])

    return document_view(
        request, header_form=POHeaderForm, formset_class=line_formset(POLineForm, 1), save=save,
        title=f"Edit {order.number}", list_url=reverse("purchasing:po_list"), success_message="Purchase order updated.",
        errors=(services.PurchasingError,),
        initial={"supplier": order.supplier_id, "warehouse": order.warehouse_id, "expected_date": order.expected_date,
                 "notes": order.notes},
        lines_initial=[{"product": l.product_id, "quantity": l.quantity, "unit_cost": l.unit_cost,
                        "vat_rate": l.vat_rate} for l in order.lines.all()],
    )


def _po_action(request, pk, func, success, **kwargs):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    try:
        func(order, user=request.user, **kwargs)
    except services.PurchasingError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, success)
    return redirect("purchasing:po_detail", pk=pk)


@login_required
@permission_required("purchasing.approve_purchaseorder", raise_exception=True)
@require_POST
def po_approve(request, pk):
    return _po_action(request, pk, services.approve_purchase_order, "Purchase order approved.")


@login_required
@permission_required("purchasing.change_purchaseorder", raise_exception=True)
@require_POST
def po_cancel(request, pk):
    return _po_action(request, pk, services.cancel_purchase_order, "Purchase order cancelled.")


@login_required
@permission_required("purchasing.add_goodsreceipt", raise_exception=True)
def po_receive(request, pk):
    """Goods receipt: enter the quantity received per line (partial receipts allowed)."""
    order = get_object_or_404(PurchaseOrder.objects.prefetch_related("lines__product"), pk=pk)
    lines = list(order.lines.all())
    if request.method == "POST":
        quantities = {}
        errors = []
        for line in lines:
            raw = request.POST.get(f"qty_{line.pk}", "").strip() or "0"
            try:
                quantities[line.pk] = forms.DecimalField(min_value=0).clean(raw)
            except forms.ValidationError:
                errors.append(f"Invalid quantity for {line.product.sku}.")
        if not errors:
            try:
                receipt = services.receive_goods(order, quantities, request.user,
                                                 notes=request.POST.get("notes", "")[:200])
            except services.PurchasingError as exc:
                errors.append(str(exc))
            else:
                messages.success(request, f"Goods receipt {receipt.number} posted; stock updated.")
                return redirect("purchasing:grn_detail", pk=receipt.pk)
        for error in errors:
            messages.error(request, error)
    return render(request, "purchasing/po_receive.html", {"order": order, "lines": lines,
                                                          "title": f"Receive goods - {order.number}"})


class BillForm(BootstrapForm):
    supplier_invoice_no = forms.CharField(max_length=40, label="Supplier invoice number")
    bill_date = forms.DateField(initial=timezone.localdate, widget=forms.DateInput)


@login_required
@permission_required("purchasing.add_supplierbill", raise_exception=True)
def po_bill(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    form = BillForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            bill = services.create_bill_from_po(order, form.cleaned_data["supplier_invoice_no"],
                                                form.cleaned_data["bill_date"], request.user)
        except services.PurchasingError as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, f"Supplier bill {bill.number} posted to accounts payable.")
            return redirect("purchasing:bill_detail", pk=bill.pk)
    return render(request, "core/generic_form.html", {"form": form, "title": f"Record supplier bill for {order.number}",
                                                      "submit_label": "Post bill"})


# ---- Goods receipts, bills, payments --------------------------------------------------------


class GRNListView(ERPListView):
    model = GoodsReceipt
    title = "Goods receipts"
    url_namespace, url_base = NS, "grn"
    columns = [("number", "Number"), ("receipt_date", "Date"), ("purchase_order.number", "PO"),
               ("purchase_order.supplier.name", "Supplier"), ("warehouse.code", "Warehouse")]
    search_fields = ["number", "purchase_order__number", "purchase_order__supplier__name"]

    def get_queryset(self):
        return super().get_queryset().select_related("purchase_order__supplier", "warehouse")


class GRNDetailView(ERPDetailView):
    model = GoodsReceipt
    url_namespace, url_base = NS, "grn"
    template_name = "purchasing/grn_detail.html"
    fields = [("number", "Number"), ("purchase_order", "Purchase order"), ("warehouse", "Warehouse"),
              ("receipt_date", "Date"), ("created_by", "Received by"), ("notes", "Notes")]


class BillFilter(django_filters.FilterSet):
    supplier = django_filters.ModelChoiceFilter(queryset=Supplier.objects.all())
    due_before = django_filters.DateFilter(field_name="due_date", lookup_expr="lte", label="Due by")

    class Meta:
        model = SupplierBill
        fields = ["status", "supplier"]


class BillListView(ERPListView):
    model = SupplierBill
    title = "Supplier bills"
    url_namespace, url_base = NS, "bill"
    columns = [("number", "Number"), ("supplier_invoice_no", "Supplier inv."), ("supplier.name", "Supplier"),
               ("bill_date", "Date"), ("due_date", "Due"), ("total", "Total"), ("balance_due", "Balance"),
               ("status", "Status")]
    search_fields = ["number", "supplier_invoice_no", "supplier__name"]
    filterset_class = BillFilter

    def get_queryset(self):
        return super().get_queryset().select_related("supplier")


class BillDetailView(ERPDetailView):
    model = SupplierBill
    url_namespace, url_base = NS, "bill"
    template_name = "purchasing/bill_detail.html"
    fields = [("number", "Number"), ("supplier_invoice_no", "Supplier invoice"), ("supplier", "Supplier"),
              ("purchase_order", "Purchase order"), ("bill_date", "Bill date"), ("due_date", "Due date"),
              ("subtotal", "Subtotal"), ("vat_amount", "VAT input"), ("total", "Total"),
              ("amount_paid", "Paid"), ("balance_due", "Balance due"), ("status", "Status"),
              ("journal_entry", "Journal entry")]


class SupplierPaymentForm(BootstrapForm):
    amount = forms.DecimalField(max_digits=14, decimal_places=3, min_value=0.001)
    payment_date = forms.DateField(initial=timezone.localdate, widget=forms.DateInput)
    method = forms.ChoiceField(choices=SupplierPayment.Method.choices)
    reference = forms.CharField(max_length=60, required=False)


@login_required
@permission_required("purchasing.add_supplierpayment", raise_exception=True)
def bill_pay(request, pk):
    bill = get_object_or_404(SupplierBill, pk=pk)
    form = SupplierPaymentForm(request.POST or None, initial={"amount": bill.balance_due})
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            payment = services.pay_supplier_bill(bill, d["amount"], d["payment_date"], d["method"], d["reference"],
                                                 request.user)
        except services.PurchasingError as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, f"Payment {payment.number} recorded.")
            return redirect("purchasing:bill_detail", pk=pk)
    return render(request, "core/generic_form.html", {"form": form, "title": f"Pay {bill.number} ({bill.supplier.name})",
                                                      "submit_label": "Record payment"})
