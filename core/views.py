from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from . import services


@never_cache
def health(request):
    """Liveness/readiness probe used by Docker, nginx and monitoring: reports database status."""
    payload = {"status": "ok", "time": timezone.now().isoformat()}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        payload["database"] = "ok"
        status = 200
    except Exception as exc:  # database down -> 503 so orchestrators can react
        payload.update(status="error", database="unavailable", detail=exc.__class__.__name__)
        status = 503
    return JsonResponse(payload, status=status)


@login_required
def dashboard(request):
    context = services.dashboard_context(request.user)
    return render(request, "core/dashboard.html", context)
