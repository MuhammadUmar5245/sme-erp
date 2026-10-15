import datetime

from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import has_perms

from . import services
from .models import Account, Expense, JournalEntry, JournalLine


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["id", "code", "name", "account_type", "is_active", "is_system", "description"]
        read_only_fields = ["is_system"]


class JournalLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source="account.code", read_only=True)

    class Meta:
        model = JournalLine
        fields = ["account", "account_code", "debit", "credit", "description"]


class JournalEntrySerializer(serializers.ModelSerializer):
    lines = JournalLineSerializer(many=True)

    class Meta:
        model = JournalEntry
        fields = ["id", "number", "entry_date", "description", "source_type", "source_id", "reference", "lines"]
        read_only_fields = ["number", "source_type", "source_id"]

    def create(self, data):
        try:
            return services.post_journal(
                data["entry_date"], data["description"],
                [(l["account"], l.get("debit", 0), l.get("credit", 0), l.get("description", "")) for l in data["lines"]],
                reference=data.get("reference", ""), user=self.context["request"].user)
        except services.UnbalancedEntry as exc:
            raise serializers.ValidationError({"lines": str(exc)})


class ExpenseSerializer(serializers.ModelSerializer):
    vat_rate = serializers.DecimalField(max_digits=5, decimal_places=2, write_only=True, default=5)

    class Meta:
        model = Expense
        fields = ["id", "number", "expense_date", "account", "payee", "description", "amount", "vat_rate",
                  "vat_amount", "total", "paid_from", "reference", "journal_entry"]
        read_only_fields = ["number", "vat_amount", "total", "journal_entry"]

    def create(self, d):
        try:
            return services.record_expense(d["expense_date"], d["account"], d["payee"], d["description"], d["amount"],
                                           d["vat_rate"], d["paid_from"], d.get("reference", ""),
                                           self.context["request"].user)
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)})


class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    search_fields = ["code", "name"]
    filterset_fields = ["account_type", "is_active"]


class JournalEntryViewSet(viewsets.ModelViewSet):
    queryset = JournalEntry.objects.prefetch_related("lines__account")
    serializer_class = JournalEntrySerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["source_type", "entry_date"]
    search_fields = ["number", "description", "reference"]


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.select_related("account")
    serializer_class = ExpenseSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["account", "paid_from"]


def _dates(request):
    today = timezone.localdate()
    parse = lambda key, default: datetime.date.fromisoformat(request.query_params[key]) if request.query_params.get(key) else default  # noqa: E731
    return parse("date_from", today.replace(month=1, day=1)), parse("date_to", today)


def _aging_json(report):
    return {
        "as_of": report["as_of"],
        "totals": report["totals"],
        "rows": [{"id": r["party"].pk, "name": r["party"].name, **{k: r[k] for k, _ in report["buckets"]},
                  "total": r["total"]} for r in report["rows"]],
    }


class FinancialReportView(APIView):
    """GET /api/v1/finance/reports/<name>/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD"""

    permission_classes = [has_perms("finance.view_journalentry")]

    def get(self, request, name):
        date_from, date_to = _dates(request)
        if name == "trial-balance":
            tb = services.trial_balance(date_to)
            data = {"as_of": date_to, "balanced": tb["balanced"], "total_debit": tb["total_debit"],
                    "total_credit": tb["total_credit"],
                    "rows": [{"code": r["account"].code, "name": r["account"].name, "debit": r["debit"],
                              "credit": r["credit"]} for r in tb["rows"]]}
        elif name == "profit-loss":
            pnl = services.profit_and_loss(date_from, date_to)
            data = {k: v for k, v in pnl.items() if k not in ("income", "expenses")}
            data["lines"] = [{"code": r["account"].code, "name": r["account"].name, "amount": r["amount"]}
                             for r in pnl["income"] + pnl["expenses"]]
        elif name == "vat-return":
            data = services.vat_return(date_from, date_to)
        elif name == "ar-aging":
            data = _aging_json(services.ar_aging(date_to))
        elif name == "ap-aging":
            data = _aging_json(services.ap_aging(date_to))
        else:
            return Response({"detail": "Unknown report."}, status=404)
        return Response(data)
