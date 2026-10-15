"""Security middleware: request context for the audit log and mandatory 2FA enforcement."""
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

from . import audit


def get_client_ip(request):
    """Client IP behind nginx (X-Forwarded-For first hop), used by axes and the audit log."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or None


class CurrentRequestMiddleware:
    """Makes the current user and IP available to audit signal handlers."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = audit.set_request_context(request)
        try:
            return self.get_response(request)
        finally:
            audit.reset_request_context(token)


TWO_FACTOR_EXEMPT_PREFIXES = ("/accounts/2fa/", "/accounts/logout/", "/accounts/login/", "/static/", "/health/")


class TwoFactorEnforcementMiddleware:
    """Session users who have a TOTP device must verify it; Admin/Accountant must enrol one.

    Token-authenticated API clients (Power BI, POS) are authenticated later by DRF, so the session
    user here is anonymous and they are not affected.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user is not None
            and user.is_authenticated
            and not user.is_verified()
            and not request.path.startswith(TWO_FACTOR_EXEMPT_PREFIXES)
        ):
            from django_otp import user_has_device

            if user_has_device(user):
                target = "accounts:2fa_verify"
            elif user.requires_2fa:
                target = "accounts:2fa_setup"
            else:
                target = None
            if target:
                if request.path.startswith("/api/"):
                    return JsonResponse({"detail": "Two-factor authentication required."}, status=403)
                return redirect(f"{reverse(target)}?next={request.get_full_path()}")
        return self.get_response(request)
