"""Quantitative feasibility (report 2.2): ROI, NPV, IRR, payback period and 5-year TCO for the ERP.

Cash-flow convention: index 0 is the upfront investment at t=0 (negative), indices 1..n are year-end
net cash flows. All maths uses Decimal-safe floats for the iterative IRR and returns rounded Decimals.
"""
from dataclasses import asdict, dataclass
from decimal import ROUND_HALF_UP, Decimal


def _d(value, places="0.001"):
    return Decimal(str(value)).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def npv(rate, cashflows):
    """Net present value; rate as a fraction (0.08 = 8%). cashflows[0] occurs today."""
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(cashflows))


def irr(cashflows, low=-0.99, high=10.0, tolerance=1e-10, max_iterations=500):
    """Internal rate of return by bisection (robust for conventional investment cash flows).

    Returns None when the NPV does not change sign over [low, high] (no IRR exists).
    """
    f_low, f_high = npv(low, cashflows), npv(high, cashflows)
    if f_low == 0:
        return low
    if f_low * f_high > 0:
        return None
    for _ in range(max_iterations):
        mid = (low + high) / 2
        f_mid = npv(mid, cashflows)
        if abs(f_mid) < tolerance or (high - low) / 2 < tolerance:
            return mid
        if f_low * f_mid < 0:
            high, f_high = mid, f_mid
        else:
            low, f_low = mid, f_mid
    return (low + high) / 2


def payback_period(cashflows, rate=None):
    """Years until cumulative (optionally discounted) cash flow turns positive, interpolated within the year."""
    cumulative = 0.0
    for t, cf in enumerate(cashflows):
        value = cf / (1 + rate) ** t if rate is not None else cf
        previous = cumulative
        cumulative += value
        if t > 0 and cumulative >= 0 > previous:
            return (t - 1) + (-previous / value)
    return None


def roi(total_benefits, total_costs):
    """Return on investment over the horizon, as a percentage."""
    if not total_costs:
        return None
    return (total_benefits - total_costs) / total_costs * 100


@dataclass
class FeasibilityInputs:
    """Defaults: Al Wadi Trading & Distribution LLC, cloud ERP, amounts in OMR."""

    licence_subscription_annual: float = 7200.0   # cloud ERP subscription + hosting, per year
    implementation_cost: float = 16500.0          # configuration, customisation, Power BI dashboards
    data_migration_cost: float = 3500.0           # cleansing and loading legacy data
    training_cost: float = 3000.0                 # initial training for ~25 users
    hardware_cost: float = 4500.0                 # tablets, barcode scanners, network upgrades
    maintenance_annual: float = 2400.0            # support, updates, Power BI Pro licences
    expected_savings_annual: float = 27500.0      # inventory carrying cost, stock-outs, admin time, collections
    benefit_growth_pct: float = 5.0               # yearly growth of benefits as the business grows
    first_year_benefit_pct: float = 60.0          # benefits ramp up while users adopt the system
    discount_rate_pct: float = 8.0                # cost of capital
    years: int = 5


def build_cashflows(i: FeasibilityInputs):
    upfront = i.implementation_cost + i.data_migration_cost + i.training_cost + i.hardware_cost
    rows = [{"year": 0, "costs": upfront, "benefits": 0.0, "net": -upfront}]
    for year in range(1, i.years + 1):
        benefits = i.expected_savings_annual * (1 + i.benefit_growth_pct / 100) ** (year - 1)
        if year == 1:
            benefits *= i.first_year_benefit_pct / 100
        costs = i.licence_subscription_annual + i.maintenance_annual
        rows.append({"year": year, "costs": costs, "benefits": benefits, "net": benefits - costs})
    cumulative = 0.0
    for row in rows:
        cumulative += row["net"]
        row["cumulative"] = cumulative
        row["discounted"] = row["net"] / (1 + i.discount_rate_pct / 100) ** row["year"]
    return rows


def evaluate(inputs: FeasibilityInputs):
    rows = build_cashflows(inputs)
    flows = [r["net"] for r in rows]
    rate = inputs.discount_rate_pct / 100
    total_costs = sum(r["costs"] for r in rows)
    total_benefits = sum(r["benefits"] for r in rows)
    irr_value = irr(flows)
    payback = payback_period(flows)
    discounted_payback = payback_period(flows, rate)
    npv_value = npv(rate, flows)
    return {
        "inputs": asdict(inputs),
        "cashflows": [{k: (_d(v) if k != "year" else v) for k, v in r.items()} for r in rows],
        "npv": _d(npv_value),
        "irr_pct": _d(irr_value * 100, "0.01") if irr_value is not None else None,
        "roi_pct": _d(roi(total_benefits, total_costs), "0.01"),
        "payback_years": _d(payback, "0.01") if payback is not None else None,
        "discounted_payback_years": _d(discounted_payback, "0.01") if discounted_payback is not None else None,
        "tco": _d(total_costs),
        "total_benefits": _d(total_benefits),
        "net_benefit": _d(total_benefits - total_costs),
        "decision": "Invest" if npv_value > 0 else "Do not invest",
        "meets_irr_hurdle": irr_value is not None and irr_value > 0.20,  # report 2.2.4: IRR above 20%
    }


def to_pdf(result, company="Al Wadi Trading & Distribution LLC"):
    import io

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.shapes import Drawing

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="ERP feasibility analysis", leftMargin=36, rightMargin=36)
    styles = getSampleStyleSheet()
    fmt = lambda v: "-" if v is None else f"{v:,.3f}"  # noqa: E731
    story = [Paragraph(f"{company} - Cloud ERP feasibility analysis", styles["Title"]),
             Paragraph("Quantitative benefits feasibility (report section 2.2). Amounts in OMR.", styles["Normal"]),
             Spacer(1, 10)]
    summary = [
        ["Measure", "Value"], ["Net present value (NPV)", fmt(result["npv"])],
        ["Internal rate of return (IRR)", f"{result['irr_pct']}%" if result["irr_pct"] is not None else "n/a"],
        ["Return on investment (ROI)", f"{result['roi_pct']}%"],
        ["Payback period", f"{result['payback_years']} years" if result["payback_years"] else "not within horizon"],
        ["Discounted payback", f"{result['discounted_payback_years']} years" if result["discounted_payback_years"]
         else "not within horizon"],
        [f"{result['inputs']['years']}-year total cost of ownership (TCO)", fmt(result["tco"])],
        ["Total benefits", fmt(result["total_benefits"])], ["Recommendation", result["decision"]],
    ]
    style = TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F4C5C")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("FONTSIZE", (0, 0), (-1, -1), 9), ("ALIGN", (1, 1), (-1, -1), "RIGHT")])
    story += [Table(summary, colWidths=[280, 180], style=style), Spacer(1, 14),
              Paragraph("Cash flows by year", styles["Heading2"])]
    flows = [["Year", "Costs", "Benefits", "Net cash flow", "Cumulative", "Discounted"]]
    for r in result["cashflows"]:
        flows.append([r["year"], fmt(r["costs"]), fmt(r["benefits"]), fmt(r["net"]), fmt(r["cumulative"]),
                      fmt(r["discounted"])])
    story += [Table(flows, style=style), Spacer(1, 14)]
    drawing = Drawing(460, 180)
    chart = VerticalBarChart()
    chart.x, chart.y, chart.width, chart.height = 40, 20, 400, 140
    chart.data = [[float(r["net"]) for r in result["cashflows"]], [float(r["cumulative"]) for r in result["cashflows"]]]
    chart.categoryAxis.categoryNames = [f"Y{r['year']}" for r in result["cashflows"]]
    chart.bars[0].fillColor = colors.HexColor("#0F4C5C")
    chart.bars[1].fillColor = colors.HexColor("#E36414")
    drawing.add(chart)
    story += [Paragraph("Net (blue) and cumulative (orange) cash flow", styles["Normal"]), drawing, Spacer(1, 10)]
    inputs = [["Assumption", "Value"]] + [[k.replace("_", " ").capitalize(), str(v)]
                                          for k, v in result["inputs"].items()]
    story += [Paragraph("Assumptions", styles["Heading2"]), Table(inputs, colWidths=[280, 180], style=style)]
    doc.build(story)
    return buffer.getvalue()
