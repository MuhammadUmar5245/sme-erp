"""End-to-end tests of the import wizard using the dirty legacy sample files."""
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from conftest import login_verified
from core.factories import WarehouseFactory
from crm.models import Customer
from finance.services import account_balance
from integrations import services
from integrations.models import ImportJob
from inventory.models import Product
from inventory.services import stock_on_hand
from purchasing.models import Supplier

pytestmark = pytest.mark.django_db
LEGACY = Path(__file__).resolve().parents[2] / "sample_data" / "legacy"


def _run(entity, filename, user=None):
    job = services.create_import_job(entity, filename, (LEGACY / filename).read_bytes(), user)
    services.set_mapping(job, job.mapping)
    return services.validate_job(job)


def _reasons(job, row):
    return next(r for r in job.results if r["row"] == row)


@pytest.fixture
def warehouses():
    return WarehouseFactory(code="MCT", name="Muscat Main Warehouse", city="Muscat"), \
        WarehouseFactory(code="SOH", name="Sohar Warehouse", city="Sohar")


def test_customer_import_cleanses_and_rejects(admin_user):
    job = _run("customers", "customers_legacy.csv", admin_user)
    assert job.mapping["name"] == "CUSTOMER NAME" and job.mapping["phone"] == "Tel"
    s = job.summary
    assert s["total"] == 23 and s["rejected"] >= 8 and s["importable"] == s["total"] - s["rejected"]

    first = _reasons(job, 2)
    assert first["data"]["name"] == "Al Meera Hypermarket" and first["data"]["phone"] == "+96824561234"
    assert first["data"]["city"] == "Muscat" and first["status"] == "fixed"
    assert any("Possible duplicate" in e or "Duplicate" in e for e in _reasons(job, 3)["errors"])  # fuzzy
    assert any("invalid e-mail" in e for e in _reasons(job, 6)["errors"])
    assert _reasons(job, 7)["status"] != "rejected"  # same name, other city = branch
    assert any("invalid Oman phone" in e for e in _reasons(job, 8)["errors"])
    assert any("required" in e for e in _reasons(job, 9)["errors"])  # missing name
    assert any("Duplicate" in e for e in _reasons(job, 12)["errors"])  # exact duplicate (Dhofar Mart)
    assert any("negative" in e for e in _reasons(job, 13)["errors"])
    assert any("Duplicate code" in e or "Duplicate" in e for e in _reasons(job, 21)["errors"])
    assert _reasons(job, 22)["data"]["city"] == "Other"

    before = Customer.objects.count()
    dry = services.dry_run(job, admin_user)
    assert dry["created"] == s["importable"] and Customer.objects.count() == before  # nothing saved
    outcome = services.commit_job(job, admin_user)
    assert outcome["created"] == s["importable"]
    assert Customer.objects.count() == before + s["importable"]
    assert Customer.objects.get(code="L-C001").phone == "+96824561234"
    with pytest.raises(services.ImportFailed):
        services.commit_job(job, admin_user)


def test_reimport_detects_existing_records(admin_user):
    services.commit_job(_run("customers", "customers_legacy.csv"), admin_user)
    again = _run("customers", "customers_legacy.csv")
    assert again.summary["importable"] == 0


def test_supplier_import(admin_user):
    job = _run("suppliers", "suppliers_legacy.csv")
    assert any("Possible duplicate" in e for e in _reasons(job, 4)["errors"])  # almarai vs Al Marai
    assert any("Duplicate" in e for e in _reasons(job, 11)["errors"])  # repeated L-S01
    assert any("negative" in e for e in _reasons(job, 9)["errors"])
    created = services.commit_job(job, admin_user)["created"]
    assert Supplier.objects.count() == created and created == job.summary["importable"]


def test_products_then_opening_stock_and_balances(admin_user, warehouses):
    products = _run("products", "products_legacy.xlsx")
    assert _reasons(products, 2)["data"]["sku"] == "LGC-1001"
    assert _reasons(products, 4)["data"]["sku"] == "LGC-1003"
    assert _reasons(products, 4)["data"]["cost_price"] == "1.250"
    assert any("negative" in e for e in _reasons(products, 7)["errors"])
    assert any("required" in e for e in _reasons(products, 9)["errors"])
    assert any("Duplicate SKU" in e for e in _reasons(products, 11)["errors"])
    assert "Sale price is below cost price" in _reasons(products, 12)["warnings"]
    out = services.commit_job(products, admin_user)
    assert out["categories_created"] >= 5
    assert Product.objects.get(sku="LGC-1002").unit == "BAG"

    stock = _run("opening_stock", "opening_stock_legacy.csv")
    assert _reasons(stock, 2)["data"]["warehouse"] == "MCT"
    assert any("negative" in e for e in _reasons(stock, 5)["errors"])
    assert any("required" in e for e in _reasons(stock, 6)["errors"])
    assert any("does not exist" in e for e in _reasons(stock, 8)["errors"])
    assert any("Duplicate" in e for e in _reasons(stock, 9)["errors"])
    assert any("unrecognised date" in e for e in _reasons(stock, 10)["errors"])
    services.commit_job(stock, admin_user)
    assert stock_on_hand(Product.objects.get(sku="LGC-1001")) == Decimal("120.000")
    assert stock_on_hand(Product.objects.get(sku="LGC-1014")) == Decimal("1200.000")

    balances = _run("opening_balances", "opening_balances_legacy.csv")
    assert _reasons(balances, 2)["data"]["account_code"] == "1000"
    assert any("both a debit and a credit" in e for e in _reasons(balances, 7)["errors"])
    assert any("not in the chart" in e for e in _reasons(balances, 8)["errors"])
    assert any("appears twice" in e for e in _reasons(balances, 10)["errors"])
    out = services.commit_job(balances, admin_user)
    assert out["journal_entry"].startswith("JE-")
    assert account_balance("1010") == Decimal("48300.000")


def test_cleansing_report_and_mapping_rules(admin_user):
    job = _run("customers", "customers_legacy.csv")
    report = services.cleansing_report_csv(job).decode("utf-8-sig")
    assert "Rejection reasons" in report and "REJECTED" in report and "FIXED" in report
    with pytest.raises(services.ImportFailed):
        services.set_mapping(job, {"code": "Cust No"})  # required fields missing
    with pytest.raises(services.ImportFailed):
        services.set_mapping(job, {"name": "Nope", "city": "Town"})


def test_bad_files_rejected():
    with pytest.raises(services.ImportFailed):
        services.create_import_job("customers", "x.pdf", b"%PDF")
    with pytest.raises(services.ImportFailed):
        services.create_import_job("customers", "x.csv", b"name,city\n")


def test_wizard_ui_flow(client, make_user):
    user = make_user("acc@alwadi.om", roles=["Accountant"])
    login_verified(client, user)
    upload = SimpleUploadedFile("suppliers_legacy.csv", (LEGACY / "suppliers_legacy.csv").read_bytes(),
                                content_type="text/csv")
    response = client.post(reverse("integrations:import_upload"), {"entity": "suppliers", "file": upload})
    job = ImportJob.objects.get()
    assert response["Location"] == reverse("integrations:import_detail", args=[job.pk])
    assert client.get(reverse("integrations:import_detail", args=[job.pk])).status_code == 200
    mapping = {f"map_{k}": v for k, v in job.mapping.items()}
    client.post(reverse("integrations:import_map", args=[job.pk]), mapping)
    page = client.get(reverse("integrations:import_detail", args=[job.pk]) + "?show=rejected")
    assert b"Possible duplicate" in page.content
    client.post(reverse("integrations:import_dry_run", args=[job.pk]))
    client.post(reverse("integrations:import_commit", args=[job.pk]))
    job.refresh_from_db()
    assert job.status == "COMMITTED"
    report = client.get(reverse("integrations:import_report", args=[job.pk]))
    assert report["Content-Type"] == "text/csv"
    assert client.get(reverse("integrations:import_list")).status_code == 200


def test_viewer_cannot_import(client, make_user):
    login_verified(client, make_user("viewer@alwadi.om", roles=["Viewer"]))
    assert client.get(reverse("integrations:import_list")).status_code == 403
