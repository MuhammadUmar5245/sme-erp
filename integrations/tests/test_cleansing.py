import datetime
from decimal import Decimal

import pytest

from integrations import cleansing as c


@pytest.mark.parametrize("raw,expected", [
    ("9123 4567", "+96891234567"),
    ("+968-9234-5678", "+96892345678"),
    ("00968 99887766", "+96899887766"),
    ("968 24561234", "+96824561234"),
    ("26 84 12 00", "+96826841200"),
    ("", ""),
])
def test_phone_normalised_to_plus_968(raw, expected):
    assert c.clean_phone(raw) == expected


@pytest.mark.parametrize("raw", ["1234", "+971 4 555 1000", "5123 4567", "abc"])
def test_invalid_phones_rejected(raw):
    with pytest.raises(c.CleansingError):
        c.clean_phone(raw)


def test_trim_and_case_normalisation():
    assert c.normalise_name("  AL MEERA   HYPERMARKET llc ") == "Al Meera Hypermarket LLC"
    assert c.normalise_name("sohar university cafeteria") == "Sohar University Cafeteria"
    assert c.normalise_name("A'Saffa Foods SAOG") == "A'Saffa Foods SAOG"  # mixed case is kept
    assert c.clean_text("  a \t b  ") == "a b"


def test_email():
    assert c.clean_email(" SEEB@NESTO.OM ") == "seeb@nesto.om"
    with pytest.raises(c.CleansingError):
        c.clean_email("alfair@@mail")


@pytest.mark.parametrize("raw,expected", [
    ("1,250.500", Decimal("1250.500")), ("OMR 2000", Decimal("2000.000")), ("1.250 OMR", Decimal("1.250")),
    (3.2, Decimal("3.200")), (45, Decimal("45.000")), ("(15)", Decimal("-15.000")), ("", None),
])
def test_decimal_parsing(raw, expected):
    assert c.clean_decimal(raw) == expected


def test_negative_amounts_rejected_when_minimum_set():
    with pytest.raises(c.CleansingError):
        c.clean_decimal("-500", minimum=Decimal("0"))
    with pytest.raises(c.CleansingError):
        c.clean_int("-30")
    with pytest.raises(c.CleansingError):
        c.clean_decimal("abc")


@pytest.mark.parametrize("raw", ["31/12/2025", "2025-12-31", "31-Dec-2025", "31.12.2025", "31 December 2025",
                                 datetime.datetime(2025, 12, 31), "46022"])
def test_date_formats_normalised(raw):
    assert c.clean_date(raw) == datetime.date(2025, 12, 31)


def test_invalid_date():
    with pytest.raises(c.CleansingError):
        c.clean_date("12.31.2025")


@pytest.mark.parametrize("raw,expected", [
    ("MCT", "Muscat"), ("masqat", "Muscat"), ("Al Seeb", "Seeb"), ("suhar", "Sohar"), ("salala", "Salalah"),
    ("Nizwah", "Nizwa"), ("Soor", "Sur"), ("bousher", "Bawshar"), ("Dubai", "Other"), ("Al Khuwair", "Muscat"),
])
def test_city_normalisation(raw, expected):
    assert c.clean_city(raw) == expected


def test_choice_mapping():
    choices = [("RETAIL", "Retail shop"), ("HORECA", "Hotel")]
    assert c.clean_choice("retail", choices) == "RETAIL"
    assert c.clean_choice("Hotel", choices) == "HORECA"
    assert c.clean_choice("baqala", choices, {"baqala": "RETAIL"}) == "RETAIL"
    assert c.clean_choice("", choices, default="RETAIL") == "RETAIL"
    with pytest.raises(c.CleansingError):
        c.clean_choice("???", choices)


def test_fuzzy_duplicate_detection():
    assert c.name_key("Al-Meera Hypermarket LLC") == c.name_key("al meera hypermarket")
    match, ratio = c.find_fuzzy_match("almarai oman llc", ["Al Marai Oman LLC", "Oman Flour Mills"])
    assert match == "Al Marai Oman LLC" and ratio >= 0.9
    assert c.find_fuzzy_match("Nizwa Grand Hotel", ["Crowne Plaza Muscat"])[0] is None
