import pytest
from django.urls import reverse

from conftest import login_verified
from core.models import SystemFeedback
from core.support import evaluation_summary

pytestmark = pytest.mark.django_db


def test_any_user_can_rate_the_system_and_report_problems(client, make_user):
    user = make_user("store@alwadi.om", roles=["Storekeeper"])
    login_verified(client, user)
    assert client.get(reverse("core:support")).status_code == 200
    client.post(reverse("core:support"), {"kind": "RATING", "area": "INVENTORY", "rating": "4"})
    client.post(reverse("core:support"), {"kind": "PROBLEM", "area": "MOBILE", "comment": "Scanner page slow"})
    assert SystemFeedback.objects.filter(user=user).count() == 2


def test_validation_requires_rating_or_comment(client, make_user):
    login_verified(client, make_user("v@alwadi.om", roles=["Viewer"]))
    client.post(reverse("core:support"), {"kind": "RATING", "area": "GENERAL"})
    client.post(reverse("core:support"), {"kind": "PROBLEM", "area": "GENERAL"})
    assert not SystemFeedback.objects.exists()


def test_evaluation_summary_and_admin_overview(client, admin_user, make_user):
    SystemFeedback.objects.create(area="REPORTS", rating=5)
    SystemFeedback.objects.create(area="REPORTS", rating=3)
    problem = SystemFeedback.objects.create(area="POWER_BI", kind="PROBLEM", comment="Refresh failed")
    summary = evaluation_summary()
    assert summary["overall"]["avg"] == 4
    reports = next(r for r in summary["rows"] if r["area"] == "REPORTS")
    assert reports["avg"] == 4 and reports["ratings"] == 2
    login_verified(client, admin_user)
    assert b"Refresh failed" in client.get(reverse("core:feedback_overview")).content
    client.post(reverse("core:feedback_resolve", args=[problem.pk]))
    problem.refresh_from_db()
    assert problem.status == "RESOLVED"
    client.logout()
    login_verified(client, make_user("mgr@alwadi.om", roles=["Manager"]))
    assert client.get(reverse("core:feedback_overview")).status_code == 403
