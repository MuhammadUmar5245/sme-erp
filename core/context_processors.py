from django.conf import settings

from .navigation import build_navigation


def erp(request):
    context = {"company": settings.COMPANY, "currency": settings.CURRENCY}
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        context["navigation"] = build_navigation(user, request.path)
    return context
