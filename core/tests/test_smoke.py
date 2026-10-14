import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_reports_database_ok(client):
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"


@pytest.mark.django_db
def test_dashboard_requires_login(client):
    response = client.get(reverse("core:dashboard"))
    assert response.status_code == 302
    assert reverse("accounts:login") in response["Location"]


@pytest.mark.django_db
def test_login_page_renders(client):
    response = client.get(reverse("accounts:login"))
    assert response.status_code == 200
    assert b"Sign in" in response.content
