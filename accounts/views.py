import django_filters
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.crud import ERPCreateView, ERPDetailView, ERPListView, ERPUpdateView

from . import services
from .forms import TokenForm, UserForm
from .models import AuditLog
from .roles import ROLE_DESCRIPTIONS

User = get_user_model()


def _safe_next(request, default="core:dashboard"):
    nxt = request.POST.get("next") or request.GET.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return nxt
    return default


# ---- Two-factor authentication ---------------------------------------------------------------


@login_required
def two_factor_setup(request):
    """QR enrolment page: scan with Google/Microsoft Authenticator, then confirm with a code."""
    device = services.get_or_create_pending_device(request.user)
    form = TokenForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if services.confirm_device(device, form.cleaned_data["token"]):
            from django_otp import login as otp_login

            otp_login(request, device)
            messages.success(request, "Two-factor authentication is now active on your account.")
            return redirect(_safe_next(request))
        form.add_error("token", "Invalid code. Check the time on your phone and try again.")
    context = {
        "form": form,
        "qr_svg": services.qr_code_svg(device),
        "secret": device.config_url.split("secret=")[1].split("&")[0],
        "required": request.user.requires_2fa,
        "next": request.GET.get("next", ""),
        "title": "Set up two-factor authentication",
    }
    return render(request, "accounts/2fa_setup.html", context)


@login_required
def two_factor_verify(request):
    """Second login step for users with a confirmed TOTP device."""
    if request.user.is_verified():
        return redirect(_safe_next(request))
    form = TokenForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        device = services.verify_user_token(request.user, form.cleaned_data["token"])
        if device is not None:
            from django_otp import login as otp_login

            otp_login(request, device)
            return redirect(_safe_next(request))
        form.add_error("token", "Invalid or expired code.")
    return render(request, "accounts/2fa_verify.html", {"form": form, "next": request.GET.get("next", "")})


@login_required
@require_POST
def two_factor_disable(request):
    if request.user.requires_2fa:
        messages.error(request, "Two-factor authentication is mandatory for your role.")
    else:
        services.reset_two_factor(request.user)
        messages.success(request, "Two-factor authentication has been turned off.")
    return redirect("accounts:profile")


@login_required
def profile(request):
    context = {
        "title": "My profile",
        "has_2fa": services.has_two_factor(request.user),
        "role_descriptions": [(g.name, ROLE_DESCRIPTIONS.get(g.name, "")) for g in request.user.groups.all()],
    }
    return render(request, "accounts/profile.html", context)


# ---- User management (Admin) ----------------------------------------------------------------


class UserFilter(django_filters.FilterSet):
    groups = django_filters.ModelChoiceFilter(queryset=Group.objects.all(), label="Role")
    is_active = django_filters.BooleanFilter(label="Active")

    class Meta:
        model = User
        fields = ["groups", "is_active", "department"]


class UserListView(ERPListView):
    model = User
    title = "Users"
    url_namespace, url_base = "accounts", "user"
    columns = [("email", "Email"), ("get_full_name", "Name"), ("department", "Department"),
               ("role_list", "Roles"), ("is_active", "Active"), ("last_login", "Last login")]
    search_fields = ["email", "first_name", "last_name"]
    filterset_class = UserFilter

    def get_queryset(self):
        return super().get_queryset().select_related("department").prefetch_related("groups")


class UserDetailView(ERPDetailView):
    model = User
    url_namespace, url_base = "accounts", "user"
    template_name = "accounts/user_detail.html"
    fields = [("email", "Email"), ("get_full_name", "Name"), ("phone", "Phone"), ("department", "Department"),
              ("role_list", "Roles"), ("is_active", "Active"), ("date_joined", "Joined"), ("last_login", "Last login")]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["has_2fa"] = services.has_two_factor(self.object)
        ctx["locked"] = services.is_locked_out(self.object)
        ctx["recent_activity"] = AuditLog.objects.filter(user=self.object)[:10]
        return ctx


class UserCreateView(ERPCreateView):
    model = User
    form_class = UserForm
    url_namespace, url_base = "accounts", "user"


class UserUpdateView(ERPUpdateView):
    model = User
    form_class = UserForm
    url_namespace, url_base = "accounts", "user"


@permission_required("accounts.change_user", raise_exception=True)
@require_POST
def user_reset_2fa(request, pk):
    user = get_object_or_404(User, pk=pk)
    services.reset_two_factor(user)
    messages.success(request, f"Two-factor authentication reset for {user.email}.")
    return redirect("accounts:user_detail", pk=pk)


@permission_required("accounts.change_user", raise_exception=True)
@require_POST
def user_unlock(request, pk):
    user = get_object_or_404(User, pk=pk)
    services.unlock_user(user)
    messages.success(request, f"{user.email} has been unlocked.")
    return redirect("accounts:user_detail", pk=pk)


# ---- Audit log (read-only, Admin) -----------------------------------------------------------


class AuditFilter(django_filters.FilterSet):
    action = django_filters.ChoiceFilter(choices=AuditLog.Action.choices)
    model = django_filters.CharFilter(lookup_expr="icontains", label="Model")
    date_from = django_filters.DateFilter(field_name="timestamp", lookup_expr="date__gte", label="From")
    date_to = django_filters.DateFilter(field_name="timestamp", lookup_expr="date__lte", label="To")

    class Meta:
        model = AuditLog
        fields = ["action", "model"]


class AuditListView(ERPListView):
    model = AuditLog
    title = "Audit log"
    url_namespace, url_base = "accounts", "audit"
    columns = [("timestamp", "Time"), ("user_email", "User"), ("action", "Action"), ("model", "Model"),
               ("object_repr", "Object"), ("ip_address", "IP")]
    search_fields = ["user_email", "object_repr", "object_id"]
    filterset_class = AuditFilter
    paginate_by = 50


class AuditDetailView(ERPDetailView):
    model = AuditLog
    url_namespace, url_base = "accounts", "audit"
    template_name = "accounts/audit_detail.html"
    fields = [("timestamp", "Time"), ("user_email", "User"), ("action", "Action"), ("model", "Model"),
              ("object_id", "Object ID"), ("object_repr", "Object"), ("ip_address", "IP address")]
