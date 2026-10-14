"""Generic, permission-checked list/detail/create/update/delete views shared by all modules.

Each module view only declares the model, columns, search fields and filters; the templates in
templates/core/ render a responsive Bootstrap table with HTMX live search, filters and pagination.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.urls import NoReverseMatch, reverse
from django.views import generic


def perm_name(model, action):
    return f"{model._meta.app_label}.{action}_{model._meta.model_name}"


class ModelPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    permission_action = "view"

    def get_permission_required(self):
        if self.permission_required:
            return super().get_permission_required()
        return [perm_name(self.model, self.permission_action)]


class ERPPageMixin:
    title = None
    url_namespace = None  # e.g. "inventory"
    url_base = None  # e.g. "product" -> product_list / product_detail / product_create / product_update

    def url_for(self, suffix, *args):
        if not (self.url_namespace and self.url_base):
            return None
        try:
            return reverse(f"{self.url_namespace}:{self.url_base}_{suffix}", args=args)
        except NoReverseMatch:
            return None

    def get_title(self):
        return self.title or self.model._meta.verbose_name_plural.capitalize()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = self.get_title()
        ctx["list_url"] = self.url_for("list")
        ctx["model_name"] = self.model._meta.verbose_name
        return ctx


class ERPListView(ModelPermissionMixin, ERPPageMixin, generic.ListView):
    template_name = "core/generic_list.html"
    paginate_by = 25
    columns = []  # [(attribute path, label), ...]
    search_fields = []
    filterset_class = None
    search_placeholder = "Search..."

    def get_queryset(self):
        qs = super().get_queryset()
        query = self.request.GET.get("q", "").strip()
        if query and self.search_fields:
            condition = Q()
            for field in self.search_fields:
                condition |= Q(**{f"{field}__icontains": query})
            qs = qs.filter(condition)
        self.filterset = None
        if self.filterset_class:
            self.filterset = self.filterset_class(self.request.GET, queryset=qs, request=self.request)
            _bootstrapify(self.filterset.form)
            qs = self.filterset.qs
        return qs

    def get_template_names(self):
        if self.request.headers.get("HX-Request") and self.request.headers.get("HX-Target") == "list-table":
            return ["core/partials/list_table.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["columns"] = self.columns
        ctx["filter_form"] = self.filterset.form if self.filterset else None
        ctx["search_enabled"] = bool(self.search_fields)
        ctx["search_placeholder"] = self.search_placeholder
        ctx["query"] = self.request.GET.get("q", "")
        ctx["detail_url_name"] = (
            f"{self.url_namespace}:{self.url_base}_detail" if self.url_namespace and self.url_for("detail", 0) else None
        )
        if self.request.user.has_perm(perm_name(self.model, "add")):
            ctx["create_url"] = self.url_for("create")
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["querystring"] = params.urlencode()
        ctx["total_count"] = ctx["paginator"].count if ctx.get("paginator") else len(ctx["object_list"])
        return ctx


def _bootstrapify(form):
    for field in form.fields.values():
        widget = field.widget
        if widget.__class__.__name__ in ("Select", "NullBooleanSelect", "SelectMultiple"):
            widget.attrs["class"] = "form-select form-select-sm"
        else:
            widget.attrs["class"] = "form-control form-control-sm"
            if widget.__class__.__name__ == "DateInput":
                widget.input_type = "date"


class ERPDetailView(ModelPermissionMixin, ERPPageMixin, generic.DetailView):
    template_name = "core/generic_detail.html"
    fields = []  # [(attribute path, label)]
    extra_template = None  # optional include rendered below the field table

    def get_title(self):
        return str(self.object)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["fields"] = self.fields
        ctx["extra_template"] = self.extra_template
        if self.request.user.has_perm(perm_name(self.model, "change")):
            ctx["update_url"] = self.url_for("update", self.object.pk)
        if self.request.user.has_perm(perm_name(self.model, "delete")):
            ctx["delete_url"] = self.url_for("delete", self.object.pk)
        return ctx


class ERPFormMixin(ERPPageMixin):
    template_name = "core/generic_form.html"
    success_message = "Saved successfully."

    def get_success_url(self):
        return self.url_for("detail", self.object.pk) or self.url_for("list") or "/"

    def form_valid(self, form):
        if hasattr(form.instance, "created_by_id") and not form.instance.pk:
            form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, self.success_message)
        return response


class ERPCreateView(ModelPermissionMixin, ERPFormMixin, generic.CreateView):
    permission_action = "add"

    def get_title(self):
        return f"New {self.model._meta.verbose_name}"


class ERPUpdateView(ModelPermissionMixin, ERPFormMixin, generic.UpdateView):
    permission_action = "change"

    def get_title(self):
        return f"Edit {self.object}"


class ERPDeleteView(ModelPermissionMixin, ERPPageMixin, generic.DeleteView):
    permission_action = "delete"
    template_name = "core/generic_confirm_delete.html"

    def get_success_url(self):
        return self.url_for("list") or "/"

    def form_valid(self, form):
        from django.db.models import ProtectedError

        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, "This record is used by other documents and cannot be deleted.")
            from django.shortcuts import redirect

            return redirect(self.url_for("detail", self.object.pk) or "/")
        messages.success(self.request, "Deleted.")
        return response
