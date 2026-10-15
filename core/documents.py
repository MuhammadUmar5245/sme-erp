"""Helpers for header + lines document forms (purchase orders, sales orders, invoices, journals)."""
from django import forms
from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import BootstrapFormMixin


class LineForm(BootstrapFormMixin, forms.Form):
    """Base for line forms: blank rows are ignored."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = field.widget.attrs.get("class", "").replace("form-control", "form-control form-control-sm").replace("form-select", "form-select form-select-sm")


def line_formset(form_class, extra=3):
    return forms.formset_factory(form_class, extra=extra, can_delete=False)


def filled_lines(formset):
    return [f.cleaned_data for f in formset.forms if f.cleaned_data and any(
        v not in (None, "", 0) for k, v in f.cleaned_data.items() if k != "DELETE")]


def document_view(request, *, header_form, formset_class, title, save, list_url, success_message,
                  submit_label="Save", lines_title="Lines", lines_help="", errors=(ValueError,),
                  initial=None, lines_initial=None):
    """Render/process a header form + lines formset; `save(header_data, lines)` returns the redirect target."""
    if request.method == "POST":
        form = header_form(request.POST)
        formset = formset_class(request.POST, prefix="lines")
    else:
        form = header_form(initial=initial or {})
        formset = formset_class(prefix="lines", initial=lines_initial)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        lines = filled_lines(formset)
        if not lines:
            form.add_error(None, "Add at least one line.")
        else:
            try:
                target = save(form.cleaned_data, lines)
            except errors as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, success_message)
                return redirect(target)
    return render(request, "core/document_form.html", {
        "form": form, "formset": formset, "title": title, "list_url": list_url, "submit_label": submit_label,
        "lines_title": lines_title, "lines_help": lines_help,
    })
