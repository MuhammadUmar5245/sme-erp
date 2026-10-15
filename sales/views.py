import django_filters
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.crud import ERPDetailView, ERPListView
from core.documents import LineForm, document_view, line_formset
from core.forms import BootstrapForm
from crm.models import Customer
from inventory.models import Product, Warehouse
from inventory.services import InsufficientStock

from . import services
from .models import CreditNote, Invoice, Payment, SalesOrder

NS = "sales"
ERRORS = (services.SalesError, InsufficientStock)


class SalesHeaderForm(BootstrapForm):
    customer = forms.ModelChoiceField(queryset=Customer.objects.filter(is_active=True))
    warehouse = forms.ModelChoiceField(queryset=Warehouse.objects.filter(is_active=True))


class OrderHeaderForm(SalesHeaderForm):
    delivery_date = forms.DateField(required=False, widget=forms.DateInput)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))


class InvoiceHeaderForm(SalesHeaderForm):
    invoice_date = forms.DateField(initial=timezone.localdate, widget=forms.DateInput)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))


class SalesLineForm(LineForm):
    product = forms.ModelChoiceField(queryset=Product.objects.filter(is_active=True))
    quantity = forms.DecimalField(max_digits=12, decimal_places=3, min_value=0.001)
    unit_price = forms.DecimalField(max_digits=14, decimal_places=3, required=False, min_value=0,
                                    help_text="Blank = list price")
    discount_pct = forms.DecimalField(max_digits=5, decimal_places=2, required=False, min_value=0, max_value=100,
                                      label="Disc %")
    vat_rate = forms.DecimalField(max_digits=5, decimal_places=2, required=False, label="VAT %")


def _customer_initial(request):
    return {"customer": request.GET.get("customer"), "warehouse": Warehouse.objects.filter(is_active=True).values_list(
        "pk", flat=True).first()}


# ---- Sales orders ----------------------------------------------------------------------------


class OrderFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="order_date", lookup_expr="gte", label="From")
    date_to = django_filters.DateFilter(field_name="order_date", lookup_expr="lte", label="To")

    class Meta:
        model = SalesOrder
        fields = ["status", "warehouse"]


class OrderListView(ERPListView):
    model = SalesOrder
    title = "Sales orders"
    url_namespace, url_base = NS, "order"
    columns = [("number", "Number"), ("order_date", "Date"), ("customer.name", "Customer"),
               ("warehouse.code", "Warehouse"), ("total", "Total"), ("status", "Status"), ("salesperson", "Sales rep")]
    search_fields = ["number", "customer__name"]
    filterset_class = OrderFilter

    def get_queryset(self):
        return super().get_queryset().select_related("customer", "warehouse", "salesperson")


class OrderDetailView(ERPDetailView):
    model = SalesOrder
    url_namespace, url_base = NS, "order"
    template_name = "sales/order_detail.html"
    fields = [("number", "Number"), ("customer", "Customer"), ("warehouse", "Warehouse"), ("order_date", "Date"),
              ("delivery_date", "Delivery"), ("status", "Status"), ("salesperson", "Sales rep"), ("notes", "Notes")]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.object.status != SalesOrder.Status.DRAFT:
            ctx.pop("update_url", None)
        ctx.pop("delete_url", None)
        return ctx


@login_required
@permission_required("sales.add_salesorder", raise_exception=True)
def order_create(request):
    def save(h, lines):
        order = services.create_sales_order(h["customer"], h["warehouse"], lines, request.user,
                                            delivery_date=h["delivery_date"], notes=h["notes"])
        return reverse("sales:order_detail", args=[order.pk])

    return document_view(request, header_form=OrderHeaderForm, formset_class=line_formset(SalesLineForm), save=save,
                         title="New sales order", list_url=reverse("sales:order_list"), errors=ERRORS,
                         success_message="Sales order saved as draft.", initial=_customer_initial(request))


@login_required
@permission_required("sales.change_salesorder", raise_exception=True)
def order_update(request, pk):
    order = get_object_or_404(SalesOrder, pk=pk)
    if order.status != SalesOrder.Status.DRAFT:
        messages.error(request, "Only draft orders can be edited.")
        return redirect("sales:order_detail", pk=pk)

    def save(h, lines):
        services.update_sales_order(order, h["customer"], h["warehouse"], lines, h["delivery_date"], h["notes"])
        return reverse("sales:order_detail", args=[pk])

    return document_view(
        request, header_form=OrderHeaderForm, formset_class=line_formset(SalesLineForm, 1), save=save,
        title=f"Edit {order.number}", list_url=reverse("sales:order_list"), errors=ERRORS,
        success_message="Sales order updated.",
        initial={"customer": order.customer_id, "warehouse": order.warehouse_id, "delivery_date": order.delivery_date,
                 "notes": order.notes},
        lines_initial=[{"product": l.product_id, "quantity": l.quantity, "unit_price": l.unit_price,
                        "discount_pct": l.discount_pct, "vat_rate": l.vat_rate} for l in order.lines.all()],
    )


def _order_action(request, pk, func, success):
    order = get_object_or_404(SalesOrder, pk=pk)
    try:
        result = func(order, user=request.user)
    except ERRORS as exc:
        messages.error(request, str(exc))
        return redirect("sales:order_detail", pk=pk)
    messages.success(request, success)
    if isinstance(result, Invoice):
        return redirect("sales:invoice_detail", pk=result.pk)
    return redirect("sales:order_detail", pk=pk)


@login_required
@permission_required("sales.change_salesorder", raise_exception=True)
@require_POST
def order_confirm(request, pk):
    return _order_action(request, pk, services.confirm_sales_order, "Order confirmed.")


@login_required
@permission_required("sales.change_salesorder", raise_exception=True)
@require_POST
def order_cancel(request, pk):
    return _order_action(request, pk, services.cancel_sales_order, "Order cancelled.")


@login_required
@permission_required("sales.add_invoice", raise_exception=True)
@require_POST
def order_invoice(request, pk):
    return _order_action(request, pk, services.invoice_sales_order, "Invoice posted: stock issued and journal created.")


# ---- Invoices --------------------------------------------------------------------------------


class InvoiceFilter(django_filters.FilterSet):
    customer = django_filters.ModelChoiceFilter(queryset=Customer.objects.all())
    date_from = django_filters.DateFilter(field_name="invoice_date", lookup_expr="gte", label="From")
    date_to = django_filters.DateFilter(field_name="invoice_date", lookup_expr="lte", label="To")

    class Meta:
        model = Invoice
        fields = ["status", "source", "warehouse"]


class InvoiceListView(ERPListView):
    model = Invoice
    url_namespace, url_base = NS, "invoice"
    columns = [("number", "Number"), ("invoice_date", "Date"), ("customer.name", "Customer"), ("due_date", "Due"),
               ("total", "Total"), ("balance_due", "Balance"), ("status", "Status"), ("source", "Source")]
    search_fields = ["number", "customer__name", "external_ref"]
    filterset_class = InvoiceFilter

    def get_queryset(self):
        return super().get_queryset().select_related("customer")


class InvoiceDetailView(ERPDetailView):
    model = Invoice
    url_namespace, url_base = NS, "invoice"
    template_name = "sales/invoice_detail.html"
    fields = [("number", "Number"), ("customer", "Customer"), ("invoice_date", "Invoice date"),
              ("due_date", "Due date"), ("warehouse", "Warehouse"), ("sales_order", "Sales order"),
              ("source", "Source"), ("external_ref", "External ref"), ("status", "Status"),
              ("salesperson", "Sales rep"), ("journal_entry", "Journal entry")]


@login_required
@permission_required("sales.view_invoice", raise_exception=True)
def invoice_print(request, pk):
    invoice = get_object_or_404(Invoice.objects.select_related("customer"), pk=pk)
    return render(request, "sales/invoice_print.html", {"invoice": invoice})


@login_required
@permission_required("sales.add_invoice", raise_exception=True)
def invoice_create(request):
    def save(h, lines):
        invoice = services.create_invoice(h["customer"], h["warehouse"], lines, request.user, h["invoice_date"],
                                          notes=h["notes"])
        return reverse("sales:invoice_detail", args=[invoice.pk])

    return document_view(request, header_form=InvoiceHeaderForm, formset_class=line_formset(SalesLineForm),
                         save=save, title="New tax invoice", list_url=reverse("sales:invoice_list"), errors=ERRORS,
                         success_message="Invoice posted: stock issued and journal created.",
                         submit_label="Post invoice", initial=_customer_initial(request),
                         lines_help="VAT 5% is applied per line. The invoice is blocked if stock is insufficient.")


class PaymentForm(BootstrapForm):
    amount = forms.DecimalField(max_digits=14, decimal_places=3, min_value=0.001)
    payment_date = forms.DateField(initial=timezone.localdate, widget=forms.DateInput)
    method = forms.ChoiceField(choices=Payment.Method.choices)
    reference = forms.CharField(max_length=60, required=False)


@login_required
@permission_required("sales.add_payment", raise_exception=True)
def invoice_pay(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    form = PaymentForm(request.POST or None, initial={"amount": invoice.balance_due})
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            payment = services.record_payment(invoice, d["amount"], d["payment_date"], d["method"], d["reference"],
                                              request.user)
        except services.SalesError as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, f"Payment {payment.number} recorded.")
            return redirect("sales:invoice_detail", pk=pk)
    return render(request, "core/generic_form.html", {
        "form": form, "title": f"Receive payment - {invoice.number} (balance OMR {invoice.balance_due:,.3f})",
        "submit_label": "Record payment"})


@login_required
@permission_required("sales.add_creditnote", raise_exception=True)
def invoice_credit(request, pk):
    """Credit note: choose quantities to credit per invoice line."""
    invoice = get_object_or_404(Invoice.objects.prefetch_related("lines__product", "lines__credit_lines"), pk=pk)
    lines = list(invoice.lines.all())
    for line in lines:
        line.creditable = line.quantity - sum((c.quantity for c in line.credit_lines.all()), 0)
    if request.method == "POST":
        items = []
        try:
            for line in lines:
                raw = request.POST.get(f"qty_{line.pk}", "").strip()
                qty = forms.DecimalField(min_value=0, required=False).clean(raw)
                if qty:
                    items.append({"invoice_line": line, "quantity": qty})
            if not items:
                raise services.SalesError("Enter a quantity for at least one line.")
            note = services.create_credit_note(invoice, items, request.POST.get("reason", "").strip() or "Return",
                                               restock=bool(request.POST.get("restock")), user=request.user)
        except (services.SalesError, forms.ValidationError) as exc:
            messages.error(request, exc.messages[0] if hasattr(exc, "messages") else str(exc))
        else:
            messages.success(request, f"Credit note {note.number} posted.")
            return redirect("sales:creditnote_detail", pk=note.pk)
    return render(request, "sales/credit_form.html", {"invoice": invoice, "lines": lines,
                                                      "title": f"Credit note for {invoice.number}"})


# ---- Payments and credit notes ---------------------------------------------------------------


class PaymentFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="payment_date", lookup_expr="gte", label="From")
    date_to = django_filters.DateFilter(field_name="payment_date", lookup_expr="lte", label="To")

    class Meta:
        model = Payment
        fields = ["method"]


class PaymentListView(ERPListView):
    model = Payment
    url_namespace, url_base = NS, "payment"
    columns = [("number", "Number"), ("payment_date", "Date"), ("customer.name", "Customer"),
               ("invoice.number", "Invoice"), ("method", "Method"), ("amount", "Amount"), ("reference", "Reference")]
    search_fields = ["number", "customer__name", "invoice__number", "reference"]
    filterset_class = PaymentFilter

    def get_queryset(self):
        return super().get_queryset().select_related("customer", "invoice")


class CreditNoteListView(ERPListView):
    model = CreditNote
    title = "Credit notes"
    url_namespace, url_base = NS, "creditnote"
    columns = [("number", "Number"), ("credit_date", "Date"), ("customer.name", "Customer"),
               ("invoice.number", "Invoice"), ("reason", "Reason"), ("total", "Total")]
    search_fields = ["number", "customer__name", "invoice__number"]

    def get_queryset(self):
        return super().get_queryset().select_related("customer", "invoice")


class CreditNoteDetailView(ERPDetailView):
    model = CreditNote
    url_namespace, url_base = NS, "creditnote"
    template_name = "sales/creditnote_detail.html"
    fields = [("number", "Number"), ("invoice", "Invoice"), ("customer", "Customer"), ("credit_date", "Date"),
              ("reason", "Reason"), ("restock", "Returned to stock"), ("subtotal", "Net"), ("vat_amount", "VAT"),
              ("total", "Total"), ("journal_entry", "Journal entry")]
