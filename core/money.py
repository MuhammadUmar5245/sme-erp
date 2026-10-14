"""Money helpers. OMR uses 3 decimal places; amounts are always Decimal, never float."""
from decimal import ROUND_HALF_UP, Decimal

THREE_PLACES = Decimal("0.001")
TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0.000")
VAT_RATE = Decimal("5.00")  # Oman VAT, percent


def D(value) -> Decimal:
    """Convert int/str/Decimal (or None) to Decimal without going through float."""
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(repr(value))
    return Decimal(str(value))


def q3(value) -> Decimal:
    """Round to baisa (3 dp), half-up."""
    return D(value).quantize(THREE_PLACES, rounding=ROUND_HALF_UP)


def q2(value) -> Decimal:
    return D(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def vat_amount(net, rate=VAT_RATE) -> Decimal:
    return q3(D(net) * D(rate) / Decimal("100"))


def format_omr(value, with_currency=True) -> str:
    text = f"{q3(value):,.3f}"
    return f"OMR {text}" if with_currency else text
