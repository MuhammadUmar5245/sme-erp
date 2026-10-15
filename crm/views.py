import django_filters
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from core.crud import ERPCreateView, ERPDetailView, ERPListView, ERPUpdateView
from core.forms import BootstrapModelForm

from . import services
from .models import OMAN_CITIES, Contact, Customer, Feedback, Interaction

NS = "crm"


class CustomerForm(BootstrapModelForm):
    class Meta:
        model = Customer
        fields = ["code", "name", "customer_type", "phone", "email", "city", "address", "vat_number",
                  "credit_limit", "payment_terms_days", "is_active", "notes"]


class ContactForm(BootstrapModelForm):
    class Meta:
        model = Contact
        fields = ["customer", "name", "position", "phone", "email", "is_primary"]


class InteractionForm(BootstrapModelForm):
    class Meta:
        model = Interaction
        fields = ["customer", "interaction_type", "interaction_date", "subject", "notes", "status", "follow_up_date"]
        widgets = {"interaction_date": forms.DateTimeInput()}


class FeedbackForm(BootstrapModelForm):
    class Meta:
        model = Feedback
        fields = ["customer", "invoice", "feedback_date", "score", "channel", "comment"]

    def clean(self):
        data = super().clean()
        if data.get("invoice") and data.get("customer") and data["invoice"].customer_id != data["customer"].pk:
            self.add_error("invoice", "This invoice belongs to another customer.")
        return data


class InitialCustomerMixin:
    """Pre-select the customer when opened from the Customer 360 page (?customer=<id>)."""

    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get("customer"):
            initial["customer"] = self.request.GET["customer"]
        return initial

    def get_success_url(self):
        return f"/crm/customers/{self.object.customer_id}/"


class CustomerFilter(django_filters.FilterSet):
    city = django_filters.ChoiceFilter(choices=OMAN_CITIES)
    is_active = django_filters.BooleanFilter(label="Active")

    class Meta:
        model = Customer
        fields = ["customer_type", "city", "is_active"]


class CustomerListView(ERPListView):
    model = Customer
    url_namespace, url_base = NS, "customer"
    columns = [("code", "Code"), ("name", "Name"), ("customer_type", "Type"), ("city", "City"), ("phone", "Phone"),
               ("credit_limit", "Credit limit"), ("is_active", "Active")]
    search_fields = ["code", "name", "phone", "email", "vat_number"]
    filterset_class = CustomerFilter


class CustomerDetailView(ERPDetailView):
    """Customer 360: orders, invoices, balance, interactions and average CSAT."""

    model = Customer
    url_namespace, url_base = NS, "customer"
    template_name = "crm/customer_360.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(services.customer_360(self.object))
        return ctx


class CustomerCreateView(ERPCreateView):
    model = Customer
    form_class = CustomerForm
    url_namespace, url_base = NS, "customer"

    def get_initial(self):
        return {"code": services.next_customer_code()}


class CustomerUpdateView(ERPUpdateView):
    model = Customer
    form_class = CustomerForm
    url_namespace, url_base = NS, "customer"


class ContactCreateView(InitialCustomerMixin, ERPCreateView):
    model = Contact
    form_class = ContactForm
    url_namespace, url_base = NS, "contact"


class ContactUpdateView(InitialCustomerMixin, ERPUpdateView):
    model = Contact
    form_class = ContactForm
    url_namespace, url_base = NS, "contact"


class InteractionFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="interaction_date", lookup_expr="date__gte", label="From")
    date_to = django_filters.DateFilter(field_name="interaction_date", lookup_expr="date__lte", label="To")

    class Meta:
        model = Interaction
        fields = ["interaction_type", "status"]


class InteractionListView(ERPListView):
    model = Interaction
    url_namespace, url_base = NS, "interaction"
    columns = [("interaction_date", "Date"), ("customer.name", "Customer"), ("interaction_type", "Type"),
               ("subject", "Subject"), ("status", "Status"), ("user", "By")]
    search_fields = ["subject", "customer__name", "notes"]
    filterset_class = InteractionFilter

    def get_queryset(self):
        return super().get_queryset().select_related("customer", "user")


class InteractionDetailView(ERPDetailView):
    model = Interaction
    url_namespace, url_base = NS, "interaction"
    template_name = "crm/interaction_detail.html"
    fields = [("interaction_date", "Date"), ("customer", "Customer"), ("interaction_type", "Type"),
              ("subject", "Subject"), ("notes", "Notes"), ("status", "Status"), ("follow_up_date", "Follow-up"),
              ("user", "Logged by")]


class InteractionCreateView(InitialCustomerMixin, ERPCreateView):
    model = Interaction
    form_class = InteractionForm
    url_namespace, url_base = NS, "interaction"

    def form_valid(self, form):
        form.instance.user = self.request.user
        if form.instance.interaction_type == Interaction.Type.COMPLAINT and "status" not in form.changed_data:
            form.instance.status = Interaction.Status.OPEN
        return super().form_valid(form)


class InteractionUpdateView(InitialCustomerMixin, ERPUpdateView):
    model = Interaction
    form_class = InteractionForm
    url_namespace, url_base = NS, "interaction"


@login_required
@permission_required("crm.change_interaction", raise_exception=True)
@require_POST
def interaction_close(request, pk):
    services.close_interaction(get_object_or_404(Interaction, pk=pk), request.user)
    messages.success(request, "Interaction closed.")
    return redirect("crm:interaction_detail", pk=pk)


class FeedbackFilter(django_filters.FilterSet):
    score = django_filters.NumberFilter()
    date_from = django_filters.DateFilter(field_name="feedback_date", lookup_expr="gte", label="From")

    class Meta:
        model = Feedback
        fields = ["score", "channel"]


class FeedbackListView(ERPListView):
    model = Feedback
    url_namespace, url_base = NS, "feedback"
    columns = [("feedback_date", "Date"), ("customer.name", "Customer"), ("score", "Score"),
               ("channel", "Channel"), ("comment", "Comment"), ("invoice", "Invoice")]
    search_fields = ["customer__name", "comment"]
    filterset_class = FeedbackFilter
    template_name = "crm/feedback_list.html"

    def get_queryset(self):
        return super().get_queryset().select_related("customer", "invoice")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["avg_csat"] = services.average_csat(self.object_list)
        return ctx


class FeedbackCreateView(InitialCustomerMixin, ERPCreateView):
    model = Feedback
    form_class = FeedbackForm
    url_namespace, url_base = NS, "feedback"

