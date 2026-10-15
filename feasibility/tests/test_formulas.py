"""Financial formulas checked against known reference values (e.g. numpy-financial documentation examples)."""
from decimal import Decimal

import pytest
from django.urls import reverse

from conftest import login_verified
from feasibility import services

pytestmark = pytest.mark.django_db


def test_npv_reference_values():
    # numpy_financial.npv(0.08, [-40000, 5000, 8000, 12000, 30000]) == 3065.22267
    assert services.npv(0.08, [-40000, 5000, 8000, 12000, 30000]) == pytest.approx(3065.22267, abs=1e-4)
    # Textbook: -1000 + 300/1.1 + 400/1.1^2 + 500/1.1^3 = -21.036814...
    assert services.npv(0.10, [-1000, 300, 400, 500]) == pytest.approx(-21.0368, abs=1e-4)
    assert services.npv(0.0, [-100, 50, 50]) == 0


def test_irr_reference_values():
    # numpy_financial.irr([-100, 39, 59, 55, 20]) == 0.28094842
    assert services.irr([-100, 39, 59, 55, 20]) == pytest.approx(0.28094842, abs=1e-7)
    # numpy_financial.irr([-150000, 15000, 25000, 35000, 45000, 60000]) == 0.0524
    assert services.irr([-150000, 15000, 25000, 35000, 45000, 60000]) == pytest.approx(0.05243, abs=1e-4)
    # At the IRR the NPV is zero.
    rate = services.irr([-1000, 300, 400, 500])
    assert services.npv(rate, [-1000, 300, 400, 500]) == pytest.approx(0, abs=1e-6)
    assert services.irr([100, 50]) is None  # no sign change -> no IRR


def test_payback_period():
    assert services.payback_period([-1000, 300, 400, 500]) == pytest.approx(2.6)
    assert services.payback_period([-1000, 500, 500]) == pytest.approx(2.0)
    assert services.payback_period([-1000, 100, 100]) is None
    # Discounted payback is longer than simple payback.
    assert services.payback_period([-1000, 500, 500, 500], 0.1) > services.payback_period([-1000, 500, 500, 500])


def test_roi():
    assert services.roi(150, 100) == 50
    assert services.roi(80, 100) == -20
    assert services.roi(10, 0) is None


def test_tco_and_cash_flows_for_default_al_wadi_case():
    inputs = services.FeasibilityInputs()
    rows = services.build_cashflows(inputs)
    upfront = 16500 + 3500 + 3000 + 4500
    assert rows[0]["net"] == -upfront
    assert rows[1]["benefits"] == pytest.approx(27500 * 0.6)
    assert rows[2]["benefits"] == pytest.approx(27500 * 1.05)
    result = services.evaluate(inputs)
    assert result["tco"] == Decimal(str(upfront + 5 * (7200 + 2400))) + Decimal("0.000")
    assert result["npv"] > 0 and result["decision"] == "Invest"
    assert result["irr_pct"] > 20 and result["meets_irr_hurdle"]
    assert 1 < result["payback_years"] < 3  # report 2.2.2: payback typically 1-3 years
    assert result["discounted_payback_years"] > result["payback_years"]


def test_unprofitable_case():
    result = services.evaluate(services.FeasibilityInputs(expected_savings_annual=5000))
    assert result["npv"] < 0 and result["decision"] == "Do not invest"
    assert result["payback_years"] is None


def test_pdf_export():
    assert services.to_pdf(services.evaluate(services.FeasibilityInputs()))[:4] == b"%PDF"


def test_calculator_page_api_and_saved_scenarios(client, api, make_user):
    accountant = make_user("acc@alwadi.om", roles=["Accountant"])
    login_verified(client, accountant)
    page = client.get(reverse("feasibility:calculator"))
    assert page.status_code == 200 and b"NPV" in page.content
    custom = client.get(reverse("feasibility:calculator") + "?" + "&".join(
        f"{k}={v}" for k, v in {**services.FeasibilityInputs().__dict__, "discount_rate_pct": 12}.items()))
    assert b"NPV @ 12" in custom.content
    pdf = client.get(reverse("feasibility:pdf"))
    assert pdf["Content-Type"] == "application/pdf"
    response = client.post(reverse("feasibility:save"), {**services.FeasibilityInputs().__dict__, "name": "Base case"})
    assert response.status_code == 302
    r = api(accountant).post("/api/v1/feasibility/calculate/", {"discount_rate_pct": 10}, format="json")
    assert r.status_code == 200 and r.json()["inputs"]["discount_rate_pct"] == 10


def test_feasibility_restricted(client, make_user):
    login_verified(client, make_user("store@alwadi.om", roles=["Storekeeper"]))
    assert client.get(reverse("feasibility:calculator")).status_code == 403
