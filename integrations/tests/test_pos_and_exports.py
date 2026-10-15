from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from conftest import login_verified
from core.factories import CustomerFactory, ProductFactory, WarehouseFactory
from integrations import services
from inventory.services import receive_stock, stock_on_hand
from sales.models import Invoice

pytestmark = pytest.mark.django_db


@pytest.fixture
def pos():
    wh = WarehouseFactory(code="MCT")
    walk_in = CustomerFactory(code="CASH", name="Cash customer (POS)")
    product = ProductFactory(sku="BEV-0001", sale_price=Decimal("0.500"))
    receive_stock(product, wh, 10, Decimal("0.300"))
    key, raw = services.create_api_key("Showroom POS 1", wh, walk_in)
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=raw)
    return {"client": client, "key": key, "raw": raw, "product": product, "wh": wh}


SALE = {"receipt_no": "MCT-POS1-000001", "lines": [{"sku": "BEV-0001", "quantity": "4"}],
        "payment": {"method": "CARD"}}
URL = "/api/v1/integrations/pos/sales/"


def test_pos_sale_creates_paid_invoice(pos):
    r = pos["client"].post(URL, SALE, format="json", HTTP_IDEMPOTENCY_KEY="sale-1")
    assert r.status_code == 201, r.content
    body = r.json()
    assert body["total"] == "2.100" and body["status"] == "PAID"
    invoice = Invoice.objects.get(pk=body["invoice_id"])
    assert invoice.source == "POS" and invoice.external_ref == "MCT-POS1-000001"
    assert stock_on_hand(pos["product"], pos["wh"]) == Decimal("6.000")
    pos["key"].refresh_from_db()
    assert pos["key"].last_used_at is not None


def test_idempotent_replay_does_not_double_post(pos):
    first = pos["client"].post(URL, SALE, format="json", HTTP_IDEMPOTENCY_KEY="sale-1")
    second = pos["client"].post(URL, SALE, format="json", HTTP_IDEMPOTENCY_KEY="sale-1")
    assert second.status_code == 200 and second["Idempotent-Replayed"] == "true"
    assert second.json() == first.json()
    assert Invoice.objects.count() == 1
    assert stock_on_hand(pos["product"], pos["wh"]) == Decimal("6.000")


def test_same_key_different_body_is_rejected(pos):
    pos["client"].post(URL, SALE, format="json", HTTP_IDEMPOTENCY_KEY="sale-1")
    other = {**SALE, "lines": [{"sku": "BEV-0001", "quantity": "1"}]}
    assert pos["client"].post(URL, other, format="json", HTTP_IDEMPOTENCY_KEY="sale-1").status_code == 422


def test_idempotency_key_required(pos):
    assert pos["client"].post(URL, SALE, format="json").status_code == 400


def test_failed_sale_can_be_retried_with_same_key(pos):
    too_many = {**SALE, "lines": [{"sku": "BEV-0001", "quantity": "50"}]}
    r = pos["client"].post(URL, too_many, format="json", HTTP_IDEMPOTENCY_KEY="sale-2")
    assert r.status_code == 409 and "Insufficient stock" in r.json()["detail"]
    assert pos["client"].post(URL, SALE, format="json", HTTP_IDEMPOTENCY_KEY="sale-2").status_code == 201


def test_unknown_sku_and_auth(pos):
    bad = {**SALE, "lines": [{"sku": "NOPE", "quantity": "1"}]}
    assert pos["client"].post(URL, bad, format="json", HTTP_IDEMPOTENCY_KEY="x").status_code == 400
    anonymous = APIClient()
    assert anonymous.post(URL, SALE, format="json", HTTP_IDEMPOTENCY_KEY="y").status_code in (401, 403)
    anonymous.credentials(HTTP_X_API_KEY="pos_wrongkey_123456789")
    assert anonymous.post(URL, SALE, format="json", HTTP_IDEMPOTENCY_KEY="y").status_code == 401
    services.revoke_api_key(pos["key"])
    assert pos["client"].post(URL, SALE, format="json", HTTP_IDEMPOTENCY_KEY="z").status_code == 401


def test_api_key_is_stored_hashed(pos):
    assert pos["raw"] not in pos["key"].key_hash and len(pos["key"].key_hash) == 64


@pytest.mark.parametrize("entity", list(services.EXPORTS))
def test_exports_csv_and_excel(api, admin_user, entity):
    CustomerFactory()
    client = api(admin_user)
    csv_resp = client.get(f"/api/v1/integrations/export/{entity}/?format=csv")
    assert csv_resp.status_code == 200 and csv_resp["Content-Type"] == "text/csv"
    xlsx = client.get(f"/api/v1/integrations/export/{entity}/?format=xlsx")
    assert xlsx.status_code == 200 and xlsx.content[:2] == b"PK"


def test_export_permissions(api, make_user):
    client = api(make_user("store@alwadi.om", roles=["Storekeeper"]))
    assert client.get("/api/v1/integrations/export/products/?format=csv").status_code == 200
    assert client.get("/api/v1/integrations/export/employees/?format=csv").status_code == 403
    assert client.get("/api/v1/integrations/export/nope/").status_code == 404


def test_export_and_apikey_pages(client, admin_user, pos):
    login_verified(client, admin_user)
    assert client.get(reverse("integrations:export_index")).status_code == 200
    assert client.get(reverse("integrations:export_download", args=["customers", "xlsx"])).status_code == 200
    page = client.post(reverse("integrations:apikey_list"), {"name": "POS 2", "warehouse": pos["wh"].pk,
                                                             "default_customer": pos["key"].default_customer_id})
    assert b"pos_" in page.content
    client.post(reverse("integrations:apikey_revoke", args=[pos["key"].pk]))
    pos["key"].refresh_from_db()
    assert not pos["key"].is_active
