from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.crud import ERPListView
from core.forms import BootstrapForm
from crm.models import Customer
from inventory.models import Warehouse

from . import services
from .importers import get_importer
from .models import APIKey, ImportJob


class UploadForm(BootstrapForm):
    entity = forms.ChoiceField(choices=ImportJob.Entity.choices, label="What are you importing?")
    file = forms.FileField(help_text="CSV or Excel (.xlsx), first row = column headings, max 10 MB")


class ImportListView(ERPListView):
    model = ImportJob
    title = "Data migration - import wizard"
    template_name = "integrations/import_list.html"
    url_namespace, url_base = "integrations", "import"
    columns = [("pk", "#"), ("created_at", "Uploaded"), ("entity", "Entity"), ("original_filename", "File"),
               ("status", "Status"), ("created_by", "By")]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["upload_form"] = UploadForm()
        ctx.pop("create_url", None)
        return ctx


@login_required
@permission_required("integrations.add_importjob", raise_exception=True)
@require_POST
def import_upload(request):
    form = UploadForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Choose an entity and a file.")
        return redirect("integrations:import_list")
    upload = form.cleaned_data["file"]
    try:
        job = services.create_import_job(form.cleaned_data["entity"], upload.name, upload.read(), request.user)
    except services.ImportFailed as exc:
        messages.error(request, str(exc))
        return redirect("integrations:import_list")
    messages.success(request, f"Read {len(job.raw_rows)} rows. Check the column mapping below.")
    return redirect("integrations:import_detail", pk=job.pk)


@login_required
@permission_required("integrations.view_importjob", raise_exception=True)
def import_detail(request, pk):
    job = get_object_or_404(ImportJob, pk=pk)
    importer = get_importer(job.entity)
    mapping_rows = [{"field": f, "selected": job.mapping.get(f.name, "")} for f in importer.fields]
    results = job.results
    status_filter = request.GET.get("show", "")
    if status_filter:
        results = [r for r in results if r["status"] == status_filter]
    return render(request, "integrations/import_detail.html", {
        "title": str(job), "job": job, "fields": importer.fields, "mapping_rows": mapping_rows,
        "sample": job.raw_rows[:5], "results": results[:300], "result_count": len(results),
        "show": status_filter,
    })


@login_required
@permission_required("integrations.change_importjob", raise_exception=True)
@require_POST
def import_map(request, pk):
    """Save the column mapping, then validate and cleanse every row (steps 2 and 3)."""
    job = get_object_or_404(ImportJob, pk=pk)
    if job.status == ImportJob.Status.COMMITTED:
        messages.error(request, "This import is already committed.")
        return redirect("integrations:import_detail", pk=pk)
    importer = get_importer(job.entity)
    mapping = {f.name: request.POST.get(f"map_{f.name}", "") for f in importer.fields}
    try:
        services.set_mapping(job, mapping)
    except services.ImportFailed as exc:
        messages.error(request, str(exc))
        return redirect("integrations:import_detail", pk=pk)
    services.validate_job(job)
    s = job.summary
    messages.info(request, f"Validated {s['total']} rows: {s['ok']} clean, {s['fixed']} fixed, {s['rejected']} rejected.")
    return redirect("integrations:import_detail", pk=pk)


@login_required
@permission_required("integrations.change_importjob", raise_exception=True)
@require_POST
def import_dry_run(request, pk):
    job = get_object_or_404(ImportJob, pk=pk)
    try:
        outcome = services.dry_run(job, request.user)
    except services.ImportFailed as exc:
        messages.error(request, str(exc))
    else:
        if "error" in outcome:
            messages.error(request, f"Dry run failed: {outcome['error']}")
        else:
            messages.success(request, f"Dry run OK - would create {outcome.get('created', 0)} records. Nothing was saved.")
    return redirect("integrations:import_detail", pk=pk)


@login_required
@permission_required("integrations.change_importjob", raise_exception=True)
@require_POST
def import_commit(request, pk):
    job = get_object_or_404(ImportJob, pk=pk)
    try:
        outcome = services.commit_job(job, request.user)
    except services.ImportFailed as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"Import committed: {outcome.get('created', 0)} records created.")
    return redirect("integrations:import_detail", pk=pk)


@login_required
@permission_required("integrations.view_importjob", raise_exception=True)
def import_report(request, pk):
    job = get_object_or_404(ImportJob, pk=pk)
    response = HttpResponse(services.cleansing_report_csv(job), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="cleansing-report-{job.pk}-{job.entity}.csv"'
    return response


@login_required
@permission_required("integrations.view_importjob", raise_exception=True)
def export_index(request):
    exports = [(entity, entity.capitalize(), request.user.has_perm(perm))
               for entity, perm in services.EXPORT_PERMISSIONS.items()]
    return render(request, "integrations/export_index.html", {"title": "Master data exports", "exports": exports})


@login_required
def export_download(request, entity, fmt):
    if entity not in services.EXPORTS or fmt not in ("csv", "xlsx"):
        return HttpResponse("Unknown export.", status=404)
    if not request.user.has_perm(services.EXPORT_PERMISSIONS[entity]):
        raise PermissionDenied
    if fmt == "csv":
        response = HttpResponse(services.export_csv(entity), content_type="text/csv")
    else:
        response = HttpResponse(services.export_xlsx(entity),
                                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{entity}.{fmt}"'
    return response


class APIKeyForm(BootstrapForm):
    name = forms.CharField(max_length=100, help_text="e.g. 'Muscat showroom POS terminal 1'")
    warehouse = forms.ModelChoiceField(queryset=Warehouse.objects.filter(is_active=True))
    default_customer = forms.ModelChoiceField(queryset=Customer.objects.filter(is_active=True),
                                              help_text="Walk-in / cash customer for sales without a customer code")


@login_required
@permission_required("integrations.view_apikey", raise_exception=True)
def apikey_list(request):
    form = APIKeyForm(request.POST or None)
    new_key = None
    if request.method == "POST":
        if not request.user.has_perm("integrations.add_apikey"):
            raise PermissionDenied
        if form.is_valid():
            key, new_key = services.create_api_key(form.cleaned_data["name"], form.cleaned_data["warehouse"],
                                                   form.cleaned_data["default_customer"], request.user)
            messages.warning(request, "Copy the API key now - it will not be shown again.")
            form = APIKeyForm()
    return render(request, "integrations/apikey_list.html", {
        "title": "POS API keys", "keys": APIKey.objects.select_related("warehouse", "default_customer"),
        "form": form, "new_key": new_key})


@login_required
@permission_required("integrations.change_apikey", raise_exception=True)
@require_POST
def apikey_revoke(request, pk):
    services.revoke_api_key(get_object_or_404(APIKey, pk=pk))
    messages.success(request, "API key revoked.")
    return redirect("integrations:apikey_list")
