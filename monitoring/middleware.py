"""Records request count, response time and errors per endpoint."""
import random
import time

from django.conf import settings

SKIP_PREFIXES = ("/static/", "/media/", "/favicon", "/health/")


class MetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "MONITORING_ENABLED", True) or request.path.startswith(SKIP_PREFIXES):
            return self.get_response(request)
        started = time.perf_counter()
        status = 500
        try:
            response = self.get_response(request)
            status = response.status_code
            return response
        finally:
            self._record(request, status, int((time.perf_counter() - started) * 1000))

    def _record(self, request, status, duration_ms):
        from .models import RequestMetric

        match = getattr(request, "resolver_match", None)
        endpoint = (match.route if match and match.route else request.path)[:200]
        user = getattr(request, "user", None)
        try:
            RequestMetric.objects.create(
                method=request.method[:8], endpoint=endpoint, view_name=(match.view_name if match else "")[:120],
                status_code=status, duration_ms=duration_ms,
                user_id=user.pk if user is not None and user.is_authenticated else None,
                is_api=request.path.startswith("/api/"),
            )
            if random.random() < 0.001:  # occasional retention clean-up
                from .services import prune

                prune()
        except Exception:  # monitoring must never break the request
            pass
