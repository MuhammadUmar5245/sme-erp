import datetime

from django import forms
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone

from core.forms import BootstrapForm

from . import builder, services


@login_required
@permission_required("reports.view_dashboard", raise_exception=True)
def dashboard(request):
    return render(request, "reports/dashboard.html", {"title": "Analytics dashboard", "kpis": services.kpis()})


@login_required
@permission_required("reports.view_dashboard", raise_exception=True)
def dashboard_data(request):
    """JSON series for the Chart.js charts."""
    return JsonResponse(services.dashboard_charts())


class BuilderForm(BootstrapForm):
    dataset = forms.ChoiceField(choices=[(k, v["label"]) for k, v in builder.DATASETS.items()])
    date_from = forms.DateField(widget=forms.DateInput, label="From")
    date_to = forms.DateField(widget=forms.DateInput, label="To")
    group_by = forms.MultipleChoiceField(required=False, widget=forms.SelectMultiple(attrs={"size": 5}),
                                         help_text="Ctrl/Cmd-click to choose several")

    def __init__(self, *args, dataset="sales", **kwargs):
        super().__init__(*args, **kwargs)
        spec = builder.DATASETS.get(dataset, builder.DATASETS["sales"])
        self.fields["group_by"].choices = [(k, label) for k, (label, _) in spec["dimensions"].items()]
        options = builder.filter_options(dataset if dataset in builder.DATASETS else "sales")
        for key in spec["filters"]:
            self.fields[f"f_{key}"] = forms.ChoiceField(
                required=False, label=key.replace("_", " ").capitalize(),
                choices=[("", "All")] + [(v, v) for v in options.get(key, [])],
                widget=forms.Select(attrs={"class": "form-select"}))


def _builder_request(request):
    today = timezone.localdate()
    dataset = request.GET.get("dataset", "sales")
    if dataset not in builder.DATASETS:
        dataset = "sales"
    data = request.GET.copy()
    data.setdefault("dataset", dataset)
    data.setdefault("date_from", today.replace(month=1, day=1).isoformat())
    data.setdefault("date_to", today.isoformat())
    if not data.getlist("group_by"):
        first = next(iter(builder.DATASETS[dataset]["dimensions"]))
        data.setlist("group_by", [first])
    return dataset, BuilderForm(data, dataset=dataset)


def _filters(form):
    return {k[2:]: v for k, v in form.cleaned_data.items() if k.startswith("f_") and v}


@login_required
@permission_required("reports.view_dashboard", raise_exception=True)
def report_builder(request):
    dataset, form = _builder_request(request)
    report, error = None, None
    if form.is_valid():
        try:
            report = builder.run_report(dataset, form.cleaned_data["group_by"], form.cleaned_data["date_from"],
                                        form.cleaned_data["date_to"], _filters(form))
        except builder.ReportError as exc:
            error = str(exc)
    preview = report["rows"][:200] if report else []
    return render(request, "reports/builder.html", {
        "title": "Report builder", "form": form, "report": report, "preview": preview, "error": error,
        "querystring": request.GET.urlencode(),
    })


@login_required
@permission_required("reports.view_dashboard", raise_exception=True)
def report_export(request, fmt):
    dataset, form = _builder_request(request)
    if not form.is_valid():
        return HttpResponse("Invalid report parameters.", status=400)
    try:
        report = builder.run_report(dataset, form.cleaned_data["group_by"], form.cleaned_data["date_from"],
                                    form.cleaned_data["date_to"], _filters(form))
    except builder.ReportError as exc:
        return HttpResponse(str(exc), status=400)
    stamp = datetime.date.today().strftime("%Y%m%d")
    name = f"sme-erp-{dataset}-{stamp}"
    if fmt == "csv":
        response = HttpResponse(builder.to_csv(report), content_type="text/csv")
    elif fmt == "xlsx":
        response = HttpResponse(builder.to_excel(report),
                                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    elif fmt == "pdf":
        response = HttpResponse(builder.to_pdf(report), content_type="application/pdf")
    else:
        return HttpResponse("Unknown format.", status=404)
    response["Content-Disposition"] = f'attachment; filename="{name}.{fmt}"'
    return response
