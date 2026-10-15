import datetime
import json

import pytest
from django.urls import reverse
from django.utils import timezone

from conftest import login_verified
from monitoring import services
from monitoring.models import HealthProbe, RequestMetric

pytestmark = pytest.mark.django_db


def test_middleware_records_requests_per_endpoint(client, make_user):
    user = make_user("viewer@alwadi.om", roles=["Viewer"])
    login_verified(client, user)
    client.get(reverse("inventory:product_list"))
    client.get("/inventory/products/does-not-exist/")
    metric = RequestMetric.objects.get(endpoint="inventory/products/")
    assert metric.status_code == 200 and metric.user_id == user.pk and metric.duration_ms >= 0
    assert RequestMetric.objects.filter(status_code=404).exists()


def test_health_check_records_probe_but_not_metric(client):
    client.get("/health/")
    assert HealthProbe.objects.filter(ok=True).count() == 1
    assert not RequestMetric.objects.filter(endpoint__contains="health").exists()


def test_summary_figures():
    now = timezone.now()
    for ms, status in [(100, 200), (200, 200), (300, 200), (400, 500), (1000, 200)]:
        RequestMetric.objects.create(method="GET", endpoint="sales/invoices/", status_code=status,
                                     duration_ms=ms, user_id=1)
    data = services.summary(24)
    assert data["request_count"] == 5
    assert data["avg_response_ms"] == 400
    assert data["p95_response_ms"] == 880  # percentile_cont interpolation
    assert data["error_count"] == 1 and data["error_rate_pct"] == 20.0
    assert data["active_users_15m"] == 1
    assert data["db_size_mb"] > 0
    assert data["endpoints"][0]["requests"] == 5
    assert data["generated_at"] >= now


def test_availability_counts_missing_probes_as_downtime():
    start = timezone.now() - datetime.timedelta(minutes=10)
    probe = HealthProbe.objects.create(ok=True)
    HealthProbe.objects.filter(pk=probe.pk).update(timestamp=start)
    for _ in range(9):
        HealthProbe.objects.create(ok=True)
    # 10 minutes at one probe / 30 s = 21 expected probes, 10 received.
    assert services.availability(start - datetime.timedelta(hours=1)) == pytest.approx(47.62, abs=0.1)
    assert services.availability(timezone.now() - datetime.timedelta(hours=1)) is not None


def test_last_backup_status(tmp_path, settings):
    settings.BACKUP_DIR = str(tmp_path)
    assert services.last_backup()["status"] == "unknown"
    finished = (timezone.now() - datetime.timedelta(hours=3)).isoformat()
    (tmp_path / "last_backup.json").write_text(json.dumps(
        {"status": "success", "file": "sme_erp_x.dump", "finished_at": finished, "size_bytes": 1000}))
    status = services.last_backup()
    assert status["status"] == "success" and status["within_rpo"] and 2.9 < status["age_hours"] < 3.1
    old = (timezone.now() - datetime.timedelta(hours=30)).isoformat()
    (tmp_path / "last_backup.json").write_text(json.dumps({"status": "success", "finished_at": old}))
    assert services.last_backup()["within_rpo"] is False


def test_prune_removes_old_metrics():
    old = RequestMetric.objects.create(method="GET", endpoint="x", status_code=200, duration_ms=1)
    RequestMetric.objects.filter(pk=old.pk).update(timestamp=timezone.now() - datetime.timedelta(days=200))
    RequestMetric.objects.create(method="GET", endpoint="y", status_code=200, duration_ms=1)
    services.prune(90)
    assert list(RequestMetric.objects.values_list("endpoint", flat=True)) == ["y"]


def test_monitoring_page_admin_only(client, admin_user, make_user):
    login_verified(client, admin_user)
    page = client.get(reverse("monitoring:dashboard") + "?hours=168")
    assert page.status_code == 200 and b"Availability" in page.content
    client.logout()
    login_verified(client, make_user("mgr@alwadi.om", roles=["Manager"]))
    assert client.get(reverse("monitoring:dashboard")).status_code == 403


def test_system_metrics_api(api, admin_user, make_user):
    data = api(admin_user).get("/api/v1/reports/system-metrics/?hours=48").json()
    assert {"availability_pct", "avg_response_ms", "p95_response_ms", "error_rate_pct", "active_users_15m",
            "db_size_mb", "last_backup", "hourly"} <= set(data)
    assert api(make_user("powerbi@alwadi.om", roles=["Viewer"])).get("/api/v1/reports/system-metrics/").status_code == 200
    assert api(make_user("store@alwadi.om", roles=["Storekeeper"])).get(
        "/api/v1/reports/system-metrics/").status_code == 403


def test_system_metrics_reporting_view():
    from django.db import connection

    RequestMetric.objects.create(method="GET", endpoint="x", status_code=500, duration_ms=50)
    with connection.cursor() as cursor:
        cursor.execute("SELECT request_count, error_count FROM reporting.fact_system_metrics_hourly")
        assert cursor.fetchone() == (1, 1)
