from django.db import models


class RequestMetric(models.Model):
    """One HTTP request: endpoint (URL pattern), status, response time and user (report 5.2.3)."""

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    method = models.CharField(max_length=8)
    endpoint = models.CharField(max_length=200, db_index=True, help_text="URL pattern, e.g. sales/invoices/<int:pk>/")
    view_name = models.CharField(max_length=120, blank=True)
    status_code = models.PositiveSmallIntegerField()
    duration_ms = models.PositiveIntegerField()
    user_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    is_api = models.BooleanField(default=False)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [models.Index(fields=["timestamp", "endpoint"])]

    def __str__(self):
        return f"{self.method} {self.endpoint} {self.status_code} {self.duration_ms}ms"


class HealthProbe(models.Model):
    """Result of each /health/ check (Docker probes every 30 s) - used for availability %."""

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ok = models.BooleanField()
    db_ms = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-timestamp"]
