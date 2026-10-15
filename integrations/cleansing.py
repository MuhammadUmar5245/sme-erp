"""Data cleansing rules for legacy imports (report 5.1.3).

Each `clean_*` function returns the cleaned value or raises CleansingError with a human-readable reason.
Callers record a "fix" whenever the cleaned value differs from the raw value.
"""
import datetime
import difflib
import re
from decimal import Decimal, InvalidOperation

from crm.models import OMAN_CITIES


class CleansingError(ValueError):
    pass


_SPACES = re.compile(r"\s+")
KEEP_UPPER = {"LLC", "SAOG", "SAOC", "WLL", "FZE", "FZC", "UAE", "KSA", "UK", "USA", "OMR", "VAT", "IT", "HQ"}
KEEP_LOWER = {"and", "of", "the", "for", "&"}


def clean_text(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return _SPACES.sub(" ", str(value)).strip()


def normalise_name(value):
    """Trim, collapse spaces and convert SHOUTING or lower-case names to Title Case (keeping LLC, SAOG ...)."""
    text = clean_text(value)
    if not text:
        return text
    letters = [ch for ch in text if ch.isalpha()]
    upper_ratio = sum(ch.isupper() for ch in letters) / len(letters) if letters else 0
    if upper_ratio >= 0.7 or upper_ratio == 0:  # SHOUTING (allowing a stray "llc") or all lower-case
        words = []
        for i, word in enumerate(text.split(" ")):
            upper = word.upper().strip(".,")
            if upper in KEEP_UPPER:
                words.append(word.upper())
            elif i > 0 and word.lower() in KEEP_LOWER:
                words.append(word.lower())
            else:
                words.append("-".join(part.capitalize() for part in word.split("-")))
        text = " ".join(words)
    return text


def clean_email(value):
    text = clean_text(value).lower()
    if not text:
        return ""
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", text):
        raise CleansingError(f"invalid e-mail '{text}'")
    return text


def clean_phone(value):
    """Normalise Omani numbers to +968XXXXXXXX (8 digits starting with 2, 7, 8 or 9)."""
    text = clean_text(value)
    if not text:
        return ""
    digits = re.sub(r"\D", "", text)
    if digits.startswith("00968"):
        digits = digits[5:]
    elif digits.startswith("968") and len(digits) == 11:
        digits = digits[3:]
    if len(digits) != 8 or digits[0] not in "2789":
        raise CleansingError(f"invalid Oman phone number '{text}'")
    return f"+968{digits}"


def clean_decimal(value, *, minimum=None, places=3):
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, (int, Decimal)):
        number = Decimal(value)
    elif isinstance(value, float):
        number = Decimal(repr(value))
    else:
        text = clean_text(value).upper().replace("OMR", "").replace("RO", "").replace(",", "").strip()
        negative = text.startswith("(") and text.endswith(")")
        text = text.strip("()")
        try:
            number = Decimal(text)
        except InvalidOperation:
            raise CleansingError(f"'{clean_text(value)}' is not a number")
        if negative:
            number = -number
    number = number.quantize(Decimal(1).scaleb(-places))
    if minimum is not None and number < minimum:
        raise CleansingError(f"negative value {number} not allowed")
    return number


def clean_int(value, *, minimum=0):
    number = clean_decimal(value, places=0)
    if number is None:
        return None
    if minimum is not None and number < minimum:
        raise CleansingError(f"negative value {number} not allowed")
    return int(number)


DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%b-%Y", "%d %b %Y", "%d %B %Y",
                "%b %d, %Y", "%Y/%m/%d", "%d-%b-%y"]


def clean_date(value):
    """Parse the many date formats found in legacy files. Day-first, as used in Oman."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    text = clean_text(value)
    if re.fullmatch(r"\d{5}(\.0)?", text):  # Excel serial number
        return datetime.date(1899, 12, 30) + datetime.timedelta(days=int(float(text)))
    text = text.split("T")[0].split(" 00:00")[0]
    for fmt in DATE_FORMATS:
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise CleansingError(f"unrecognised date '{text}'")


CITY_ALIASES = {
    "muscat": "Muscat", "mct": "Muscat", "masqat": "Muscat", "muscat city": "Muscat", "ruwi": "Muscat",
    "muttrah": "Muscat", "al khuwair": "Muscat", "qurum": "Muscat", "ghubra": "Muscat",
    "seeb": "Seeb", "al seeb": "Seeb", "as seeb": "Seeb", "mawaleh": "Seeb", "al mawaleh": "Seeb",
    "bawshar": "Bawshar", "bousher": "Bawshar", "bausher": "Bawshar",
    "sohar": "Sohar", "suhar": "Sohar", "sohaar": "Sohar",
    "salalah": "Salalah", "salala": "Salalah", "dhofar": "Salalah",
    "nizwa": "Nizwa", "nizwah": "Nizwa", "sur": "Sur", "soor": "Sur", "ibri": "Ibri", "barka": "Barka",
    "barkha": "Barka", "rustaq": "Rustaq", "rustaq city": "Rustaq",
}
VALID_CITIES = {value for value, _ in OMAN_CITIES}


def clean_city(value):
    text = clean_text(value)
    if not text:
        return ""
    key = text.lower().replace("-", " ").replace("_", " ")
    key = _SPACES.sub(" ", key)
    if key in CITY_ALIASES:
        return CITY_ALIASES[key]
    title = text.title()
    if title in VALID_CITIES:
        return title
    close = difflib.get_close_matches(key, list(CITY_ALIASES), n=1, cutoff=0.8)
    if close:
        return CITY_ALIASES[close[0]]
    return "Other"


def clean_choice(value, choices, aliases=None, default=None):
    """Map free text to a model choice value (by value, label or alias)."""
    text = clean_text(value)
    if not text:
        if default is not None:
            return default
        raise CleansingError("value is required")
    key = text.lower()
    for stored, label in choices:
        if key in (str(stored).lower(), str(label).lower()):
            return stored
    if aliases and key in aliases:
        return aliases[key]
    raise CleansingError(f"'{text}' is not one of {', '.join(str(c[0]) for c in choices)}")


# ---- Duplicate detection ---------------------------------------------------------------------

_NOISE_WORDS = {"llc", "saog", "saoc", "co", "company", "est", "establishment", "trading", "the", "and", "&", "l.l.c"}


def name_key(name):
    """Comparison key for names: lower-case, no punctuation, no legal-form noise words."""
    words = re.sub(r"[^a-z0-9 ]", " ", clean_text(name).lower().replace("-", " ")).split()
    return " ".join(w for w in words if w not in _NOISE_WORDS)


def similarity(a, b):
    return difflib.SequenceMatcher(None, name_key(a), name_key(b)).ratio()


def find_fuzzy_match(name, candidates, threshold=0.9):
    """Return (candidate, ratio) for the most similar candidate name above the threshold."""
    best, best_ratio = None, 0.0
    key = name_key(name)
    if not key:
        return None, 0.0
    for candidate in candidates:
        ratio = difflib.SequenceMatcher(None, key, name_key(candidate)).ratio()
        if ratio > best_ratio:
            best, best_ratio = candidate, ratio
    if best_ratio >= threshold:
        return best, best_ratio
    return None, best_ratio
