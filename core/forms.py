from django import forms


class BootstrapFormMixin:
    """Adds Bootstrap 5 classes to every widget and HTML5 date inputs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css = "form-select"
            elif isinstance(widget, forms.CheckboxSelectMultiple):
                css = ""
            else:
                css = "form-control"
            if isinstance(widget, forms.DateInput):
                widget.input_type = "date"
                widget.format = "%Y-%m-%d"
            if isinstance(widget, forms.DateTimeInput):
                widget.input_type = "datetime-local"
                widget.format = "%Y-%m-%dT%H:%M"
            if isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("rows", 3)
            if css:
                widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()


class BootstrapModelForm(BootstrapFormMixin, forms.ModelForm):
    pass


class BootstrapForm(BootstrapFormMixin, forms.Form):
    pass
