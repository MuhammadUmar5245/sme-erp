"""System monitoring figures: uptime, response times, error rate, active users, DB size, last backup."""
import datetime
import json
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.db.models import Avg, Count, Q
from django.utils import timezone

from .models import HealthProbe, RequestMetric

PROCESS_STARTED = timezone.now()
HEALTH_INTERVAL_SECONDS = 30


def record_probe(ok, db_ms=0):
    try:
        HealthProbe.objects.create(ok=ok, db_ms=db_ms)
    except Exception:
        pass


def prune(days=None):
    days = days or getattr(settings, "MONITORING_RETENTION_DAYS", 90)
    cutoff = timezone.now() - datetime.timedelta(days=days)
    RequestMetric.objects.filter(timestamp__lt=cutoff).delete()
    HealthProbe.objects.filter(timestamp__lt=cutoff).delete()


def _percentile(since, pct=0.95):
    with connection.cursor() as cursor:
        cursor.execute("SELECT percentile_cont(%s) WITHIN GROUP (ORDER BY duration_ms) FROM monitoring_requestmetric "
                       "WHERE timestamp >= %s", [pct, since])
        value = cursor.fetchone()[0]
    return round(value) if value is not None else None


def database_size_bytes():
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_database_size(current_database())")
        return cursor.fetchone()[0]


def last_backup():
    path = Path(getattr(settings, "BACKUP_DIR", "/backups")) / "last_backup.json"
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {"status": "unknown", "message": "No backup has been recorded yet."}
    try:
        finished = datetime.datetime.fromisoformat(data.get("finished_at"))
        data["age_hours"] = round((timezone.now() - finished).total_seconds() / 3600, 1)
        # RPO = 24 h: warn if the last successful backup is older than that.
        data["within_rpo"] = data.get("status") == "success" and data["age_hours"] <= 24
    except (TypeError, ValueError):
        pass
    return data


def availability(since, now=None):
    """Share of expected 30-second health probes that succeeded.

    When the application or database is down no successful probe is recorded, so availability is
    measured against the probes that *should* have happened since monitoring started.
    """
    now = now or timezone.now()
    probes = HealthProbe.objects.filter(timestamp__gte=since)
    first = HealthProbe.objects.order_by("timestamp").values_list("timestamp", flat=True).first()
    if first is None:
        return None
    window_start = max(since, first)
    expected = max(1, int((now - window_start).total_seconds() // HEALTH_INTERVAL_SECONDS) + 1)
    ok = probes.filter(ok=True).count()
    return round(min(ok / expected, 1.0) * 100, 2)


def summary(hours=24):
    now = timezone.now()
    since = now - datetime.timedelta(hours=hours)
    window = RequestMetric.objects.filter(timestamp__gte=since)
    totals = window.aggregate(count=Count("id"), avg=Avg("duration_ms"),
                              errors=Count("id", filter=Q(status_code__gte=500)),
                              client_errors=Count("id", filter=Q(status_code__gte=400, status_code__lt=500)))
    count = totals["count"] or 0
    endpoints = list(
        window.values("method", "endpoint")
        .annotate(requests=Count("id"), avg_ms=Avg("duration_ms"), errors=Count("id", filter=Q(status_code__gte=500)))
        .order_by("-requests")[:25]
    )
    for row in endpoints:
        row["avg_ms"] = round(row["avg_ms"] or 0)
    uptime = now - PROCESS_STARTED
    return {
        "generated_at": now,
        "period_hours": hours,
        "uptime_since": PROCESS_STARTED,
        "uptime_seconds": int(uptime.total_seconds()),
        "availability_pct": availability(since),
        "request_count": count,
        "avg_response_ms": round(totals["avg"] or 0),
        "p95_response_ms": _percentile(since),
        "error_count": totals["errors"],
        "error_rate_pct": round(totals["errors"] / count * 100, 2) if count else 0.0,
        "client_error_count": totals["client_errors"],
        "active_users_15m": RequestMetric.objects.filter(timestamp__gte=now - datetime.timedelta(minutes=15),
                                                         user_id__isnull=False).values("user_id").distinct().count(),
        "db_size_mb": round(database_size_bytes() / 1024 / 1024, 1),
        "last_backup": last_backup(),
        "endpoints": endpoints,
    }


def hourly_series(hours=24):
    since = timezone.now() - datetime.timedelta(hours=hours)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT date_trunc('hour', timestamp AT TIME ZONE %s) AS h, COUNT(*), AVG(duration_ms), "
            "SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) FROM monitoring_requestmetric "
            "WHERE timestamp >= %s GROUP BY 1 ORDER BY 1", [settings.TIME_ZONE, since])
        rows = cursor.fetchall()
    return {"labels": [r[0].strftime("%d %b %H:00") for r in rows], "requests": [r[1] for r in rows],
            "avg_ms": [round(float(r[2] or 0)) for r in rows], "errors": [int(r[3]) for r in rows]}
