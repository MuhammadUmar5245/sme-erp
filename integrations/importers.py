"""Entity importers for legacy data migration: field specs, validation/cleansing and commit.

Pipeline (report 5.1.3): map fields -> cleanse -> validate -> detect duplicates -> dry run -> commit.
"""
import datetime
import difflib
import re
from dataclasses import dataclass, field
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from crm.models import Customer
from finance.models import Account
from inventory.models import Category, Product, Warehouse
from purchasing.models import Supplier

from . import cleansing as c

FUZZY_THRESHOLD = 0.9


@dataclass
class Field:
    name: str
    label: str
    kind: str = "text"  # text | name | phone | email | decimal | money | int | date | city | choice
    required: bool = False
    aliases: tuple = ()
    choices: tuple = ()
    choice_aliases: dict = field(default_factory=dict)
    default: object = None


def _clean(f, raw):
    if f.kind == "text":
        return c.clean_text(raw)
    if f.kind == "name":
        return c.normalise_name(raw)
    if f.kind == "phone":
        return c.clean_phone(raw)
    if f.kind == "email":
        return c.clean_email(raw)
    if f.kind == "money":
        return c.clean_decimal(raw, minimum=Decimal("0"))
    if f.kind == "decimal":
        return c.clean_decimal(raw)
    if f.kind == "int":
        return c.clean_int(raw)
    if f.kind == "date":
        return c.clean_date(raw)
    if f.kind == "city":
        return c.clean_city(raw)
    if f.kind == "choice":
        return c.clean_choice(raw, f.choices, f.choice_aliases, f.default)
    raise ValueError(f.kind)


def _to_json(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime.date):
        return value.isoformat()
    return value


def _from_json(f, value):
    if value in (None, ""):
        return f.default if value is None and f.default is not None else value
    if f.kind in ("money", "decimal"):
        return Decimal(value)
    if f.kind == "date":
        return datetime.date.fromisoformat(value)
    return value


def _is_change(raw, cleaned):
    """True when cleansing changed the value (ignores pure type differences from Excel cells)."""
    if isinstance(raw, (int, float, Decimal)) and isinstance(cleaned, (int, Decimal)):
        return Decimal(str(raw)) != Decimal(str(cleaned))
    if isinstance(raw, datetime.datetime) and isinstance(cleaned, datetime.date):
        return raw.date() != cleaned
    if isinstance(raw, datetime.date) and isinstance(cleaned, datetime.date):
        return raw != cleaned
    return str(_to_json(cleaned)) != str(raw).strip()


def _normalise_header(text):
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


class Importer:
    entity = None
    fields: list = []

    # ---- mapping -----------------------------------------------------------------------------
    def suggest_mapping(self, headers):
        """Auto-map file columns to target fields by name, alias or close match."""
        normalised = {_normalise_header(h): h for h in headers}
        mapping = {}
        for f in self.fields:
            candidates = [_normalise_header(x) for x in (f.name, f.label, *f.aliases)]
            hit = next((normalised[k] for k in candidates if k in normalised), None)
            if hit is None:
                close = difflib.get_close_matches(_normalise_header(f.label), list(normalised), n=1, cutoff=0.85)
                hit = normalised[close[0]] if close else None
            if hit is not None and hit not in mapping.values():
                mapping[f.name] = hit
        return mapping

    # ---- validation --------------------------------------------------------------------------
    def validate(self, raw_rows, mapping):
        results = []
        for index, raw in enumerate(raw_rows, start=2):  # row 1 is the header in the source file
            result = {"row": index, "status": "ok", "data": {}, "fixes": [], "errors": [], "warnings": []}
            for f in self.fields:
                source = mapping.get(f.name)
                value = raw.get(source) if source else None
                raw_text = c.clean_text(value)
                try:
                    cleaned = _clean(f, value)
                except c.CleansingError as exc:
                    result["errors"].append(f"{f.label}: {exc}")
                    cleaned = None
                if f.required and cleaned in (None, ""):
                    if not any(e.startswith(f"{f.label}:") for e in result["errors"]):
                        result["errors"].append(f"{f.label}: required value is missing")
                elif cleaned not in (None, "") and raw_text and _is_change(value, cleaned):
                    result["fixes"].append(f"{f.label}: '{str(value).strip()}' -> '{_to_json(cleaned)}'")
                result["data"][f.name] = _to_json(cleaned)
            self.check_row(result)
            results.append(result)
        self.check_duplicates(results)
        for result in results:
            if result["errors"]:
                result["status"] = "rejected"
            elif result["fixes"]:
                result["status"] = "fixed"
        return results

    def check_row(self, result):
        """Entity-specific checks (references, business rules)."""

    def check_duplicates(self, results):
        """Exact and fuzzy duplicate detection. Default: by `key_field` and fuzzy on `name`."""
        key_field = getattr(self, "key_field", None)
        seen_keys, seen_names = {}, []
        existing_keys = self.existing_keys()
        existing_names = self.existing_names()
        for result in results:
            if result["errors"]:
                continue
            data = result["data"]
            key = (data.get(key_field) or "").upper() if key_field else ""
            if key:
                if key in seen_keys:
                    result["errors"].append(f"Duplicate {key_field} '{key}' (same as row {seen_keys[key]})")
                    continue
                if key in existing_keys:
                    result["errors"].append(f"{key_field} '{key}' already exists in the ERP")
                    continue
                seen_keys[key] = result["row"]
            name = data.get("name")
            if not name:
                continue
            exact = next((r for n, r, _ in seen_names if c.name_key(n) == c.name_key(name)
                          and self.same_party(data, _)), None)
            if exact:
                result["errors"].append(f"Duplicate of row {exact} (same name '{name}')")
                continue
            match, ratio = c.find_fuzzy_match(name, [n for n, _r, d in seen_names if self.same_party(data, d)],
                                              FUZZY_THRESHOLD)
            if match:
                row = next(r for n, r, _ in seen_names if n == match)
                result["errors"].append(f"Possible duplicate of row {row} '{match}' ({ratio:.0%} similar name)")
                continue
            match, ratio = c.find_fuzzy_match(name, existing_names, FUZZY_THRESHOLD)
            if match:
                result["errors"].append(f"Possible duplicate of existing record '{match}' ({ratio:.0%} similar)")
                continue
            seen_names.append((name, result["row"], data))

    def same_party(self, a, b):
        return True

    def existing_keys(self):
        return set()

    def existing_names(self):
        return []

    def typed(self, result):
        return {f.name: _from_json(f, result["data"].get(f.name)) for f in self.fields}

    # ---- commit ------------------------------------------------------------------------------
    def commit(self, results, user, as_of=None):
        """Create records for every non-rejected row. Returns {created: n, ...}."""
        raise NotImplementedError


class CustomerImporter(Importer):
    entity = "customers"
    key_field = "code"
    fields = [
        Field("code", "Customer code", aliases=("customer code", "cust code", "cust_no", "account no", "id")),
        Field("name", "Customer name", "name", True, aliases=("customer name", "customer", "cust name", "company")),
        Field("customer_type", "Customer type", "choice", aliases=("type", "segment", "channel"),
              choices=tuple(Customer.Type.choices), default=Customer.Type.RETAIL,
              choice_aliases={"shop": "RETAIL", "grocery": "RETAIL", "baqala": "RETAIL", "wholesale": "WHOLESALE",
                              "supermarket": "HYPERMARKET", "hypermarket": "HYPERMARKET", "hotel": "HORECA",
                              "restaurant": "HORECA", "cafe": "HORECA", "school": "INSTITUTION",
                              "hospital": "INSTITUTION", "government": "INSTITUTION"}),
        Field("phone", "Phone", "phone", aliases=("telephone", "mobile", "tel", "gsm", "contact no")),
        Field("email", "E-mail", "email", aliases=("email address", "mail")),
        Field("city", "City", "city", True, aliases=("town", "location", "wilayat")),
        Field("address", "Address", aliases=("street", "address line")),
        Field("vat_number", "VAT number", aliases=("vat", "vat no", "tax number", "vatin")),
        Field("credit_limit", "Credit limit", "money", aliases=("credit limit omr", "limit")),
        Field("payment_terms_days", "Payment terms (days)", "int", aliases=("terms", "credit days", "payment terms")),
    ]

    def same_party(self, a, b):
        # Same-name shops in different cities are branches, not duplicates - unless the phone matches.
        return a.get("city") == b.get("city") or (a.get("phone") and a.get("phone") == b.get("phone"))

    def existing_keys(self):
        return {code.upper() for code in Customer.objects.values_list("code", flat=True)}

    def existing_names(self):
        return list(Customer.objects.values_list("name", flat=True))

    def commit(self, results, user, as_of=None):
        from core.numbering import next_number

        created = 0
        for result in results:
            if result["status"] == "rejected":
                continue
            d = self.typed(result)
            Customer.objects.create(
                code=d["code"] or next_number("CUS").replace("CUS-", "C"), name=d["name"],
                customer_type=d["customer_type"] or Customer.Type.RETAIL, phone=d["phone"] or "",
                email=d["email"] or "", city=d["city"] or "Muscat", address=d["address"] or "",
                vat_number=d["vat_number"] or "", credit_limit=d["credit_limit"] or 0,
                payment_terms_days=d["payment_terms_days"] if d["payment_terms_days"] is not None else 30,
                notes="Imported from legacy system", created_by=user,
            )
            created += 1
        return {"created": created}


class SupplierImporter(Importer):
    entity = "suppliers"
    key_field = "code"
    fields = [
        Field("code", "Supplier code", aliases=("supplier code", "vendor code", "vendor no", "id")),
        Field("name", "Supplier name", "name", True, aliases=("supplier", "vendor", "vendor name", "company")),
        Field("contact_person", "Contact person", "name", aliases=("contact", "contact name")),
        Field("phone", "Phone", "phone", aliases=("telephone", "mobile", "tel")),
        Field("email", "E-mail", "email", aliases=("email address",)),
        Field("city", "City", "text", aliases=("town", "location")),
        Field("country", "Country", "name", default="Oman"),
        Field("vat_number", "VAT number", aliases=("vat", "vat no", "tax number")),
        Field("payment_terms_days", "Payment terms (days)", "int", aliases=("terms", "credit days")),
    ]

    def existing_keys(self):
        return {code.upper() for code in Supplier.objects.values_list("code", flat=True)}

    def existing_names(self):
        return list(Supplier.objects.values_list("name", flat=True))

    def commit(self, results, user, as_of=None):
        created = 0
        for result in results:
            if result["status"] == "rejected":
                continue
            d = self.typed(result)
            code = d["code"] or f"S{Supplier.objects.count() + 1:04d}"
            while Supplier.objects.filter(code=code).exists():
                code = f"S{int(code[1:] or 0) + 1:04d}" if code[1:].isdigit() else code + "1"
            Supplier.objects.create(
                code=code, name=d["name"], contact_person=d["contact_person"] or "", phone=d["phone"] or "",
                email=d["email"] or "", city=c.clean_city(d["city"]) if d["city"] else "Muscat",
                country=d["country"] or "Oman", vat_number=d["vat_number"] or "",
                payment_terms_days=d["payment_terms_days"] if d["payment_terms_days"] is not None else 30,
                created_by=user,
            )
            created += 1
        return {"created": created}


UNIT_ALIASES = {"pc": "PCS", "pcs": "PCS", "piece": "PCS", "pieces": "PCS", "each": "PCS", "ea": "PCS",
                "ctn": "CTN", "carton": "CTN", "cartons": "CTN", "case": "CTN", "box": "BOX", "boxes": "BOX",
                "pack": "PACK", "pk": "PACK", "packet": "PACK", "bag": "BAG", "sack": "BAG", "kg": "KG", "kgs": "KG",
                "kilo": "KG", "ltr": "LTR", "l": "LTR", "litre": "LTR", "liter": "LTR", "btl": "BTL", "bottle": "BTL"}


class ProductImporter(Importer):
    entity = "products"
    key_field = "sku"
    fields = [
        Field("sku", "SKU", "text", True, aliases=("item code", "item no", "product code", "code", "sku code")),
        Field("name", "Product name", "name", True, aliases=("description", "item name", "product", "item")),
        Field("category", "Category", "name", True, aliases=("group", "item group", "product category")),
        Field("unit", "Unit", "choice", aliases=("uom", "unit of measure"), choices=tuple(Product.Unit.choices),
              choice_aliases=UNIT_ALIASES, default="PCS"),
        Field("cost_price", "Cost price", "money", True, aliases=("cost", "purchase price", "unit cost")),
        Field("sale_price", "Sale price", "money", True, aliases=("price", "selling price", "retail price", "rsp")),
        Field("reorder_level", "Reorder level", "money", aliases=("min stock", "reorder point", "minimum")),
        Field("barcode", "Barcode", aliases=("ean", "upc")),
    ]

    def check_row(self, result):
        d = result["data"]
        if d.get("sku"):
            d["sku"] = d["sku"].upper().replace(" ", "-")
        if d.get("cost_price") and d.get("sale_price") and Decimal(d["sale_price"]) < Decimal(d["cost_price"]):
            result["warnings"].append("Sale price is below cost price")

    def existing_keys(self):
        return {sku.upper() for sku in Product.objects.values_list("sku", flat=True)}

    def check_duplicates(self, results):
        # Products are unique by SKU only (different SKUs may legitimately share similar names).
        seen = {}
        existing = self.existing_keys()
        for result in results:
            sku = (result["data"].get("sku") or "").upper()
            if not sku or result["errors"]:
                continue
            if sku in seen:
                result["errors"].append(f"Duplicate SKU '{sku}' (same as row {seen[sku]})")
            elif sku in existing:
                result["errors"].append(f"SKU '{sku}' already exists in the ERP")
            else:
                seen[sku] = result["row"]

    def commit(self, results, user, as_of=None):
        created = categories = 0
        for result in results:
            if result["status"] == "rejected":
                continue
            d = self.typed(result)
            category = Category.objects.filter(name__iexact=d["category"]).first()
            if category is None:
                code = re.sub(r"[^A-Z]", "", d["category"].upper())[:6] or "CAT"
                while Category.objects.filter(code=code).exists():
                    code = f"{code[:5]}{Category.objects.count() % 10}"
                category = Category.objects.create(code=code, name=d["category"], created_by=user)
                categories += 1
            Product.objects.create(
                sku=d["sku"], name=d["name"], category=category, unit=d["unit"] or "PCS", barcode=d["barcode"] or "",
                cost_price=d["cost_price"], sale_price=d["sale_price"], reorder_level=d["reorder_level"] or 0,
                created_by=user,
            )
            created += 1
        return {"created": created, "categories_created": categories}


class OpeningStockImporter(Importer):
    entity = "opening_stock"
    fields = [
        Field("sku", "SKU", "text", True, aliases=("item code", "product code", "code")),
        Field("warehouse", "Warehouse", "text", True, aliases=("store", "location", "wh", "warehouse code")),
        Field("quantity", "Quantity", "decimal", True, aliases=("qty", "qty on hand", "quantity on hand", "on hand", "stock", "balance")),
        Field("unit_cost", "Unit cost", "money", aliases=("cost", "avg cost", "average cost")),
        Field("stock_date", "Stock date", "date", aliases=("date", "as of", "count date")),
    ]

    def _warehouse(self, text):
        key = c.clean_text(text).lower()
        for wh in Warehouse.objects.all():
            if key in (wh.code.lower(), wh.name.lower()) or wh.code.lower() in key or wh.city.lower() in key:
                return wh
        return None

    def check_row(self, result):
        d = result["data"]
        if d.get("sku"):
            d["sku"] = d["sku"].upper()
            if not Product.objects.filter(sku__iexact=d["sku"]).exists():
                result["errors"].append(f"SKU '{d['sku']}' does not exist (import products first)")
        if d.get("warehouse"):
            wh = self._warehouse(d["warehouse"])
            if wh is None:
                result["errors"].append(f"Unknown warehouse '{d['warehouse']}'")
            elif wh.code != d["warehouse"]:
                result["fixes"].append(f"Warehouse: '{d['warehouse']}' -> '{wh.code}'")
                d["warehouse"] = wh.code
        if d.get("quantity") is not None and Decimal(d["quantity"]) <= 0:
            result["errors"].append(f"Quantity: negative or zero quantity {d['quantity']} not allowed")

    def check_duplicates(self, results):
        seen = {}
        for result in results:
            d = result["data"]
            key = (d.get("sku"), d.get("warehouse"))
            if result["errors"] or not all(key):
                continue
            if key in seen:
                result["errors"].append(f"Duplicate SKU/warehouse (same as row {seen[key]})")
            else:
                seen[key] = result["row"]

    def commit(self, results, user, as_of=None):
        from inventory.services import record_opening_stock

        created = 0
        for result in results:
            if result["status"] == "rejected":
                continue
            d = self.typed(result)
            product = Product.objects.get(sku__iexact=d["sku"])
            day = d["stock_date"] or as_of or timezone.localdate()
            moment = timezone.make_aware(datetime.datetime.combine(day, datetime.time(6, 0)))
            record_opening_stock(product, Warehouse.objects.get(code=d["warehouse"]), d["quantity"],
                                 d["unit_cost"] if d["unit_cost"] is not None else product.cost_price, user, moment)
            created += 1
        return {"created": created}


class OpeningBalanceImporter(Importer):
    entity = "opening_balances"
    fields = [
        Field("account_code", "Account code", "text", True, aliases=("account", "gl code", "acct", "code")),
        Field("debit", "Debit", "money", aliases=("dr", "debit amount")),
        Field("credit", "Credit", "money", aliases=("cr", "credit amount")),
        Field("balance_date", "Balance date", "date", aliases=("date", "as of")),
    ]

    def check_row(self, result):
        d = result["data"]
        code = (d.get("account_code") or "").split(" ")[0].split("-")[0].strip()
        if code and code != d.get("account_code"):
            result["fixes"].append(f"Account code: '{d['account_code']}' -> '{code}'")
            d["account_code"] = code
        if code and not Account.objects.filter(code=code).exists():
            result["errors"].append(f"Account '{code}' is not in the chart of accounts")
        debit, credit = Decimal(d.get("debit") or 0), Decimal(d.get("credit") or 0)
        if debit and credit:
            result["errors"].append("A line cannot have both a debit and a credit")
        if not debit and not credit and not result["errors"]:
            result["errors"].append("Both debit and credit are empty or zero")

    def check_duplicates(self, results):
        seen = {}
        for result in results:
            code = result["data"].get("account_code")
            if result["errors"] or not code:
                continue
            if code in seen:
                result["errors"].append(f"Account {code} appears twice (row {seen[code]})")
            else:
                seen[code] = result["row"]

    def commit(self, results, user, as_of=None):
        from finance.services import post_opening_balances

        lines, dates = [], []
        for result in results:
            if result["status"] == "rejected":
                continue
            d = self.typed(result)
            lines.append((d["account_code"], d["debit"] or 0, d["credit"] or 0))
            if d["balance_date"]:
                dates.append(d["balance_date"])
        if not lines:
            return {"created": 0}
        entry = post_opening_balances(max(dates) if dates else (as_of or timezone.localdate()), lines, user)
        return {"created": len(lines), "journal_entry": entry.number}


IMPORTERS = {cls.entity: cls() for cls in (CustomerImporter, SupplierImporter, ProductImporter,
                                           OpeningStockImporter, OpeningBalanceImporter)}


def get_importer(entity):
    return IMPORTERS[entity]


def commit_rows(importer, results, user, as_of=None):
    with transaction.atomic():
        return importer.commit(results, user, as_of)
