import django_filters
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from core.crud import ERPCreateView, ERPDetailView, ERPListView, ERPUpdateView
from core.documents import LineForm, document_view, line_formset
from core.forms import BootstrapForm, BootstrapModelForm

from . import services
from .models import Account, Expense, JournalEntry

NS = "finance"


class AccountForm(BootstrapModelForm):
    class Meta:
        model = Account
        fields = ["code", "name", "account_type", "is_active", "description"]


class AccountListView(ERPListView):
    model = Account
    title = "Chart of accounts"
    url_namespace, url_base = NS, "account"
    columns = [("code", "Code"), ("name", "Name"), ("account_type", "Type"), ("is_system", "System"),
               ("is_active", "Active")]
    search_fields = ["code", "name"]
    paginate_by = 100


class AccountDetailView(ERPDetailView):
    model = Account
    url_namespace, url_base = NS, "account"
    template_name = "finance/account_detail.html"
    fields = [("code", "Code"), ("name", "Name"), ("account_type", "Type"), ("is_system", "System account"),
              ("description", "Description")]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["balance"] = services.account_balance(self.object.code)
        ctx["lines"] = self.object.lines.select_related("entry").order_by("-entry__entry_date", "-id")[:30]
        return ctx


class AccountCreateView(ERPCreateView):
    model = Account
    form_class = AccountForm
    url_namespace, url_base = NS, "account"


class AccountUpdateView(ERPUpdateView):
    model = Account
    form_class = AccountForm
    url_namespace, url_base = NS, "account"


class JournalFilter(django_filters.FilterSet):
    source_type = django_filters.ChoiceFilter(choices=JournalEntry.Source.choices, label="Source")
    date_from = django_filters.DateFilter(field_name="entry_date", lookup_expr="gte", label="From")
    date_to = django_filters.DateFilter(field_name="entry_date", lookup_expr="lte", label="To")

    class Meta:
        model = JournalEntry
        fields = ["source_type"]


class JournalListView(ERPListView):
    model = JournalEntry
    title = "Journal entries"
    url_namespace, url_base = NS, "journal"
    columns = [("number", "Number"), ("entry_date", "Date"), ("description", "Description"),
               ("source_type", "Source"), ("reference", "Reference")]
    search_fields = ["number", "description", "reference"]
    filterset_class = JournalFilter


class JournalDetailView(ERPDetailView):
    model = JournalEntry
    url_namespace, url_base = NS, "journal"
    template_name = "finance/journal_detail.html"
    fields = [("number", "Number"), ("entry_date", "Date"), ("description", "Description"),
              ("source_type", "Source"), ("reference", "Reference"), ("created_by", "Posted by")]


class JournalHeaderForm(BootstrapForm):
    entry_date = forms.DateField(initial=timezone.localdate, widget=forms.DateInput)
    description = forms.CharField(max_length=255)
    reference = forms.CharField(max_length=60, required=False)


class JournalLineForm(LineForm):
    account = forms.ModelChoiceField(queryset=Account.objects.filter(is_active=True))
    debit = forms.DecimalField(max_digits=14, decimal_places=3, required=False, min_value=0)
    credit = forms.DecimalField(max_digits=14, decimal_places=3, required=False, min_value=0)
    description = forms.CharField(max_length=200, required=False)


@login_required
@permission_required("finance.add_journalentry", raise_exception=True)
def journal_create(request):
    def save(header, lines):
        entry = services.post_journal(
            header["entry_date"], header["description"],
            [(l["account"], l.get("debit") or 0, l.get("credit") or 0, l.get("description", "")) for l in lines],
            reference=header.get("reference", ""), user=request.user)
        return reverse("finance:journal_detail", args=[entry.pk])

    return document_view(request, header_form=JournalHeaderForm, formset_class=line_formset(JournalLineForm, 4),
                         title="New manual journal entry", save=save, list_url=reverse("finance:journal_list"),
                         success_message="Journal entry posted.", submit_label="Post entry",
                         lines_help="Total debits must equal total credits.")


class ExpenseForm(BootstrapForm):
    expense_date = forms.DateField(initial=timezone.localdate, widget=forms.DateInput)
    account = forms.ModelChoiceField(queryset=Account.objects.filter(account_type=Account.Type.EXPENSE,
                                                                      is_active=True), label="Expense account")
    payee = forms.CharField(max_length=120)
    description = forms.CharField(max_length=200)
    amount = forms.DecimalField(max_digits=14, decimal_places=3, min_value=0.001, label="Net amount (OMR)")
    vat_rate = forms.DecimalField(max_digits=5, decimal_places=2, initial=5, label="VAT %")
    paid_from = forms.ChoiceField(choices=Expense.PaidFrom.choices)
    reference = forms.CharField(max_length=60, required=False)


class ExpenseListView(ERPListView):
    model = Expense
    url_namespace, url_base = NS, "expense"
    columns = [("number", "Number"), ("expense_date", "Date"), ("account", "Account"), ("payee", "Payee"),
               ("description", "Description"), ("amount", "Net"), ("vat_amount", "VAT"), ("total", "Total")]
    search_fields = ["number", "payee", "description"]


class ExpenseDetailView(ERPDetailView):
    model = Expense
    url_namespace, url_base = NS, "expense"
    fields = [("number", "Number"), ("expense_date", "Date"), ("account", "Account"), ("payee", "Payee"),
              ("description", "Description"), ("amount", "Net amount"), ("vat_amount", "VAT input"),
              ("total", "Total"), ("paid_from", "Paid from"), ("reference", "Reference"),
              ("journal_entry", "Journal entry")]


class ExpenseCreateView(ERPCreateView):
    model = Expense
    form_class = ExpenseForm
    url_namespace, url_base = NS, "expense"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.pop("instance", None)
        return kwargs

    def form_valid(self, form):
        d = form.cleaned_data
        try:
            self.object = services.record_expense(d["expense_date"], d["account"], d["payee"], d["description"],
                                                  d["amount"], d["vat_rate"], d["paid_from"], d["reference"],
                                                  self.request.user)
        except ValueError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, f"Expense {self.object.number} recorded and posted.")
        return redirect(self.get_success_url())


class PeriodForm(BootstrapForm):
    date_from = forms.DateField(widget=forms.DateInput, required=False, label="From")
    date_to = forms.DateField(widget=forms.DateInput, required=False, label="To")


@login_required
@permission_required("finance.view_journalentry", raise_exception=True)
def reports(request):
    """Trial balance, P&L, VAT return, AR aging and AP aging on one tabbed page."""
    today = timezone.localdate()
    form = PeriodForm(request.GET or None)
    date_from, date_to = today.replace(month=1, day=1), today
    if form.is_valid():
        date_from = form.cleaned_data["date_from"] or date_from
        date_to = form.cleaned_data["date_to"] or date_to
    else:
        form = PeriodForm(initial={"date_from": date_from, "date_to": date_to})
    report = request.GET.get("report", "pnl")
    context = {
        "title": "Financial reports", "form": form, "report": report, "date_from": date_from, "date_to": date_to,
        "tabs": [("pnl", "Profit & loss"), ("tb", "Trial balance"), ("vat", "VAT return"),
                 ("ar", "AR aging"), ("ap", "AP aging")],
    }
    if report == "tb":
        context["tb"] = services.trial_balance(date_to)
    elif report == "vat":
        context["vat"] = services.vat_return(date_from, date_to)
    elif report == "ar":
        context["aging"] = services.ar_aging(date_to)
        context["aging_title"] = "Accounts receivable aging"
    elif report == "ap":
        context["aging"] = services.ap_aging(date_to)
        context["aging_title"] = "Accounts payable aging"
    else:
        context["pnl"] = services.profit_and_loss(date_from, date_to)
    return render(request, "finance/reports.html", context)

