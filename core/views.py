import time

from django.apps import apps
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
    started = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        payload["database"] = "ok"
        payload["db_ms"] = round((time.perf_counter() - started) * 1000, 1)
        status = 200
    except Exception as exc:  # database down -> 503 so orchestrators can react
        payload.update(status="error", database="unavailable", detail=exc.__class__.__name__)
        status = 503
    if apps.is_installed("monitoring") and status == 200:
        from monitoring.services import record_probe

        record_probe(True, int(payload["db_ms"]))
    return JsonResponse(payload, status=status)


@login_required
def dashboard(request):
    context = services.dashboard_context(request.user)
    return render(request, "core/dashboard.html", context)
