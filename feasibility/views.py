from dataclasses import asdict, fields

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from core.forms import BootstrapForm
from core.permissions import has_perms

from . import services
from .models import FeasibilityStudy

LABELS = {
    "licence_subscription_annual": ("Licence / subscription per year (OMR)", "Cloud ERP subscription and hosting"),
    "implementation_cost": ("Implementation (OMR, one-off)", "Configuration, customisation, Power BI dashboards"),
    "data_migration_cost": ("Data migration (OMR, one-off)", "Cleansing and loading legacy data"),
    "training_cost": ("Training (OMR, one-off)", "Initial user training"),
    "hardware_cost": ("Hardware and devices (OMR, one-off)", "Tablets, scanners, network"),
    "maintenance_annual": ("Maintenance and support per year (OMR)", "Support contract, updates, Power BI Pro"),
    "expected_savings_annual": ("Expected savings per year (OMR)", "Full-year benefit once adopted"),
    "benefit_growth_pct": ("Benefit growth per year (%)", ""),
    "first_year_benefit_pct": ("Year-1 benefit realisation (%)", "Adoption ramp-up"),
    "discount_rate_pct": ("Discount rate (%)", "Cost of capital"),
    "years": ("Horizon (years)", "TCO period"),
}


class FeasibilityForm(BootstrapForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        defaults = asdict(services.FeasibilityInputs())
        for f in fields(services.FeasibilityInputs):
            label, help_text = LABELS[f.name]
            if f.name == "years":
                field = forms.IntegerField(min_value=1, max_value=15)
            else:
                field = forms.DecimalField(min_value=0, max_digits=14, decimal_places=3)
            field.label, field.help_text, field.initial = label, help_text, defaults[f.name]
            field.widget.attrs["class"] = "form-control"
            self.fields[f.name] = field

    def to_inputs(self):
        return services.FeasibilityInputs(**{k: (int(v) if k == "years" else float(v))
                                             for k, v in self.cleaned_data.items()})


@login_required
@permission_required("feasibility.view_feasibilitystudy", raise_exception=True)
def calculator(request):
    form = FeasibilityForm(request.GET or None)
    inputs = form.to_inputs() if form.is_bound and form.is_valid() else services.FeasibilityInputs()
    if not form.is_bound:
        form = FeasibilityForm()
    result = services.evaluate(inputs)
    chart = {"labels": [f"Year {r['year']}" for r in result["cashflows"]],
             "net": [float(r["net"]) for r in result["cashflows"]],
             "cumulative": [float(r["cumulative"]) for r in result["cashflows"]],
             "costs": [float(r["costs"]) for r in result["cashflows"]],
             "benefits": [float(r["benefits"]) for r in result["cashflows"]]}
    return render(request, "feasibility/calculator.html", {
        "title": "ERP feasibility calculator", "form": form, "r": result, "chart": chart,
        "querystring": request.GET.urlencode(), "studies": FeasibilityStudy.objects.all()[:10],
    })


@login_required
@permission_required("feasibility.view_feasibilitystudy", raise_exception=True)
def export_pdf(request):
    form = FeasibilityForm(request.GET or None)
    inputs = form.to_inputs() if form.is_bound and form.is_valid() else services.FeasibilityInputs()
    response = HttpResponse(services.to_pdf(services.evaluate(inputs)), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="erp-feasibility-al-wadi.pdf"'
    return response


@login_required
@permission_required("feasibility.add_feasibilitystudy", raise_exception=True)
def save_study(request):
    form = FeasibilityForm(request.POST)
    if form.is_valid():
        inputs = form.to_inputs()
        study = FeasibilityStudy.objects.create(name=request.POST.get("name") or "Scenario", inputs=asdict(inputs),
                                                results=services.evaluate(inputs), created_by=request.user)
        messages.success(request, f"Scenario '{study.name}' saved.")
        return redirect(f"{reverse('feasibility:calculator')}?{_qs(study.inputs)}")
    messages.error(request, "Check the inputs.")
    return redirect("feasibility:calculator")


def _qs(inputs):
    from urllib.parse import urlencode

    return urlencode(inputs)


@login_required
@permission_required("feasibility.view_feasibilitystudy", raise_exception=True)
def open_study(request, pk):
    study = get_object_or_404(FeasibilityStudy, pk=pk)
    return redirect(f"{reverse('feasibility:calculator')}?{_qs(study.inputs)}")


class InputSerializer(serializers.Serializer):
    licence_subscription_annual = serializers.FloatField(min_value=0, required=False)
    implementation_cost = serializers.FloatField(min_value=0, required=False)
    data_migration_cost = serializers.FloatField(min_value=0, required=False)
    training_cost = serializers.FloatField(min_value=0, required=False)
    hardware_cost = serializers.FloatField(min_value=0, required=False)
    maintenance_annual = serializers.FloatField(min_value=0, required=False)
    expected_savings_annual = serializers.FloatField(min_value=0, required=False)
    benefit_growth_pct = serializers.FloatField(required=False)
    first_year_benefit_pct = serializers.FloatField(min_value=0, required=False)
    discount_rate_pct = serializers.FloatField(min_value=0, required=False)
    years = serializers.IntegerField(min_value=1, max_value=15, required=False)


class CalculateView(APIView):
    """POST /api/v1/feasibility/calculate/ - ROI, NPV, IRR, payback and TCO (omitted inputs use defaults)."""

    permission_classes = [has_perms("feasibility.view_feasibilitystudy")]
    serializer_class = InputSerializer

    def post(self, request):
        body = InputSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        return Response(services.evaluate(services.FeasibilityInputs(**body.validated_data)))
