from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class FeasibilityStudy(models.Model):
    """A saved ROI/NPV/IRR/TCO scenario."""

    name = models.CharField(max_length=120)
    inputs = models.JSONField(default=dict)
    results = models.JSONField(default=dict, encoder=DjangoJSONEncoder)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "feasibility studies"

    def __str__(self):
        return self.name
