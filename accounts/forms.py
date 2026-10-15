from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from core.forms import BootstrapForm, BootstrapModelForm

from .roles import ROLE_DESCRIPTIONS, ROLES

User = get_user_model()


def role_choices():
    return [(role, f"{role} - {ROLE_DESCRIPTIONS[role]}") for role in ROLES]


class TokenForm(BootstrapForm):
    token = forms.CharField(
        label="6-digit code",
        max_length=8,
        widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "inputmode": "numeric", "autofocus": True}),
    )


class UserForm(BootstrapModelForm):
    roles = forms.MultipleChoiceField(choices=role_choices, widget=forms.CheckboxSelectMultiple, required=False)
    password = forms.CharField(
        widget=forms.PasswordInput(render_value=False),
        required=False,
        help_text="At least 12 characters. Leave blank to keep the current password.",
    )

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "phone", "department", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["roles"].initial = list(self.instance.groups.values_list("name", flat=True))
        else:
            self.fields["password"].required = True
            self.fields["password"].help_text = "At least 12 characters."

    def clean_email(self):
        return self.cleaned_data["email"].lower()

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            validate_password(password, self.instance)
        return password

    def save(self, commit=True):
        from .services import set_roles

        user = super().save(commit=False)
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        user.save()
        set_roles(user, self.cleaned_data.get("roles", []))
        return user

