"""Integrations: legacy import wizard, cleansing reports, master-data exports and the POS sales API."""
import csv
import datetime
import hashlib
import hmac
import io
import json
import secrets
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from .importers import commit_rows, get_importer
from .models import APIKey, IdempotencyRecord, ImportJob

MAX_IMPORT_ROWS = 20000
MAX_FILE_BYTES = 10 * 1024 * 1024


class ImportFailed(ValueError):
    pass


# ---- File reading ----------------------------------------------------------------------------


def _json_safe(value):
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def read_tabular_file(name, content):
    """Read CSV or Excel bytes into (headers, rows as list of dicts)."""
    if len(content) > MAX_FILE_BYTES:
        raise ImportFailed("File is larger than 10 MB.")
    lower = name.lower()
    if lower.endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook

        try:
            sheet = load_workbook(io.BytesIO(content), read_only=True, data_only=True).worksheets[0]
        except Exception as exc:
            raise ImportFailed(f"Cannot read Excel file: {exc}")
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            raise ImportFailed("The file is empty.")
        headers = [str(h).strip() if h is not None else f"Column {i + 1}" for i, h in enumerate(rows[0])]
        data = [dict(zip(headers, (_json_safe(v) for v in row))) for row in rows[1:]
                if any(v not in (None, "") for v in row)]
    elif lower.endswith((".csv", ".txt")):
        for encoding in ("utf-8-sig", "cp1256", "latin-1"):
            try:
                text = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(io.StringIO(text), dialect)
        rows = [row for row in reader]
        if not rows:
            raise ImportFailed("The file is empty.")
        headers = [h.strip() or f"Column {i + 1}" for i, h in enumerate(rows[0])]
        data = [dict(zip(headers, row)) for row in rows[1:] if any(cell.strip() for cell in row)]
    else:
        raise ImportFailed("Upload a .csv or .xlsx file.")
    if len(data) > MAX_IMPORT_ROWS:
        raise ImportFailed(f"Too many rows ({len(data)}); the limit is {MAX_IMPORT_ROWS}.")
    if not data:
        raise ImportFailed("The file has a header row but no data.")
    return headers, data


# ---- Import wizard ---------------------------------------------------------------------------


def create_import_job(entity, filename, content, user=None):
    """Step 1 - upload: read the file and suggest a column mapping."""
    importer = get_importer(entity)
    headers, rows = read_tabular_file(filename, content)
    return ImportJob.objects.create(entity=entity, original_filename=filename, headers=headers, raw_rows=rows,
                                    mapping=importer.suggest_mapping(headers), created_by=user)


def set_mapping(job, mapping):
    """Step 2 - column mapping. Required target fields must be mapped."""
    importer = get_importer(job.entity)
    mapping = {k: v for k, v in mapping.items() if v}
    unknown = [v for v in mapping.values() if v not in job.headers]
    if unknown:
        raise ImportFailed(f"Unknown column(s): {', '.join(unknown)}")
    missing = [f.label for f in importer.fields if f.required and f.name not in mapping]
    if missing:
        raise ImportFailed(f"Map the required field(s): {', '.join(missing)}")
    job.mapping = mapping
    job.status = ImportJob.Status.MAPPED
    job.save(update_fields=["mapping", "status"])
    return job


def validate_job(job):
    """Step 3 - cleanse and validate every row; store per-row results and the summary."""
    importer = get_importer(job.entity)
    results = importer.validate(job.raw_rows, job.mapping)
    summary = {
        "total": len(results),
        "ok": sum(r["status"] == "ok" for r in results),
        "fixed": sum(r["status"] == "fixed" for r in results),
        "rejected": sum(r["status"] == "rejected" for r in results),
        "duplicates": sum(any("uplicate" in e for e in r["errors"]) for r in results),
        "fixes_applied": sum(len(r["fixes"]) for r in results),
        "warnings": sum(len(r["warnings"]) for r in results),
    }
    summary["importable"] = summary["ok"] + summary["fixed"]
    job.results, job.summary, job.status = results, summary, ImportJob.Status.VALIDATED
    job.save(update_fields=["results", "summary", "status"])
    return job


class _Rollback(Exception):
    pass


def dry_run(job, user=None):
    """Step 4 - run the real commit inside a transaction that is always rolled back."""
    if job.status not in (ImportJob.Status.VALIDATED,):
        raise ImportFailed("Validate the file before the dry run.")
    importer = get_importer(job.entity)
    outcome = {}
    try:
        with transaction.atomic():
            outcome = importer.commit(job.results, user)
            raise _Rollback
    except _Rollback:
        pass
    except Exception as exc:
        outcome = {"error": str(exc)}
    job.dry_run = {**outcome, "at": timezone.now().isoformat()}
    job.save(update_fields=["dry_run"])
    return job.dry_run


def commit_job(job, user=None):
    """Step 5 - commit all valid rows atomically."""
    if job.status == ImportJob.Status.COMMITTED:
        raise ImportFailed("This import has already been committed.")
    if job.status != ImportJob.Status.VALIDATED:
        raise ImportFailed("Validate the file before committing.")
    importer = get_importer(job.entity)
    try:
        outcome = commit_rows(importer, job.results, user)
    except Exception as exc:
        job.status = ImportJob.Status.FAILED
        job.summary = {**job.summary, "error": str(exc)}
        job.save(update_fields=["status", "summary"])
        raise ImportFailed(f"Import failed and was rolled back: {exc}")
    job.status = ImportJob.Status.COMMITTED
    job.committed_at = timezone.now()
    job.summary = {**job.summary, "committed": outcome}
    job.save(update_fields=["status", "committed_at", "summary"])
    return outcome


def cleansing_report_rows(job):
    importer = get_importer(job.entity)
    headers = ["Source row", "Status", "Rejection reasons", "Fixes applied", "Warnings"] + [f.label for f in importer.fields]
    rows = []
    for r in job.results:
        rows.append([r["row"], r["status"].upper(), "; ".join(r["errors"]), "; ".join(r["fixes"]),
                     "; ".join(r["warnings"])] + [r["data"].get(f.name) for f in importer.fields])
    return headers, rows


def cleansing_report_csv(job):
    headers, rows = cleansing_report_rows(job)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([f"Cleansing report - import #{job.pk} {job.get_entity_display()} - {job.original_filename}"])
    writer.writerow([f"{k}: {v}" for k, v in job.summary.items() if k != "committed"])
    writer.writerow([])
    writer.writerow(headers)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


# ---- Master-data export ----------------------------------------------------------------------

EXPORTS = {
    "customers": ("crm.Customer", ["code", "name", "customer_type", "phone", "email", "city", "address", "vat_number",
                                   "credit_limit", "payment_terms_days", "is_active"]),
    "suppliers": ("purchasing.Supplier", ["code", "name", "contact_person", "phone", "email", "city", "country",
                                          "vat_number", "payment_terms_days", "is_active"]),
    "products": ("inventory.Product", ["sku", "name", "category__name", "unit", "barcode", "cost_price", "sale_price",
                                       "vat_rate", "reorder_level", "reorder_quantity", "is_active"]),
    "categories": ("inventory.Category", ["code", "name", "description"]),
    "warehouses": ("inventory.Warehouse", ["code", "name", "city", "address", "is_active"]),
    "accounts": ("finance.Account", ["code", "name", "account_type", "is_active"]),
    "employees": ("hr.Employee", ["employee_no", "first_name", "last_name", "department__name", "job_title",
                                  "hire_date", "phone", "email", "city", "nationality", "is_active"]),
    "departments": ("hr.Department", ["code", "name", "is_active"]),
}
EXPORT_PERMISSIONS = {
    "customers": "crm.view_customer", "suppliers": "purchasing.view_supplier", "products": "inventory.view_product",
    "categories": "inventory.view_category", "warehouses": "inventory.view_warehouse",
    "accounts": "finance.view_account", "employees": "hr.view_employee", "departments": "hr.view_department",
}


def export_rows(entity):
    from django.apps import apps

    model_label, fields = EXPORTS[entity]
    model = apps.get_model(model_label)
    rows = list(model.objects.order_by("pk").values_list(*fields))
    return [f.replace("__name", "") for f in fields], rows


def export_csv(entity):
    headers, rows = export_rows(entity)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows([[_json_safe(v) for v in row] for row in rows])
    return buffer.getvalue().encode("utf-8-sig")


def export_xlsx(entity):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    headers, rows = export_rows(entity)
    wb = Workbook()
    ws = wb.active
    ws.title = entity[:30]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in rows:
        ws.append([float(v) if isinstance(v, Decimal) else v for v in row])
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


# ---- API keys and the POS integration --------------------------------------------------------


def _hash_key(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


def create_api_key(name, warehouse, default_customer, user=None):
    """Return (APIKey, raw_key). The raw key is shown once and never stored."""
    raw = "pos_" + secrets.token_urlsafe(32)
    key = APIKey.objects.create(name=name, prefix=raw[:12], key_hash=_hash_key(raw), warehouse=warehouse,
                                default_customer=default_customer, created_by=user)
    return key, raw


def authenticate_api_key(raw):
    if not raw or len(raw) < 12:
        return None
    key = APIKey.objects.filter(prefix=raw[:12], is_active=True).select_related("warehouse",
                                                                               "default_customer").first()
    if key is None or not hmac.compare_digest(key.key_hash, _hash_key(raw)):
        return None
    APIKey.objects.filter(pk=key.pk).update(last_used_at=timezone.now())
    return key


def revoke_api_key(key):
    key.is_active = False
    key.save(update_fields=["is_active"])
    return key


class POSError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def request_fingerprint(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def process_pos_sale(api_key, idempotency_key, payload):
    """Create (or replay) a POS sale. Returns (status_code, response_body, replayed).

    The idempotency record and the invoice are written in the same transaction: a retried request
    with the same Idempotency-Key returns the original response instead of posting a second invoice.
    Failed requests leave no record, so the client may retry them with the same key.
    """
    from crm.models import Customer
    from inventory.models import Product, Warehouse
    from inventory.services import InsufficientStock
    from sales.models import Payment
    from sales.services import SalesError, create_invoice, record_payment

    if not idempotency_key or len(idempotency_key) > 100:
        raise POSError("Header Idempotency-Key is required (max 100 characters).")
    fingerprint = request_fingerprint(payload)
    try:
        with transaction.atomic():
            record, created = IdempotencyRecord.objects.select_for_update().get_or_create(
                api_key=api_key, key=idempotency_key, defaults={"request_hash": fingerprint})
            if not created:
                if record.request_hash != fingerprint:
                    raise POSError("Idempotency-Key was already used with a different request body.", 422)
                return record.status_code, record.response, True

            lines_in = payload.get("lines") or []
            if not isinstance(lines_in, list) or not lines_in:
                raise POSError("'lines' must be a non-empty list.")
            warehouse = api_key.warehouse
            if payload.get("warehouse"):
                warehouse = Warehouse.objects.filter(code=payload["warehouse"]).first()
                if warehouse is None:
                    raise POSError(f"Unknown warehouse '{payload['warehouse']}'.")
            customer = api_key.default_customer
            if payload.get("customer_code"):
                customer = Customer.objects.filter(code=payload["customer_code"]).first()
                if customer is None:
                    raise POSError(f"Unknown customer '{payload['customer_code']}'.")
            lines = []
            for item in lines_in:
                product = Product.objects.filter(sku=str(item.get("sku", "")).upper(), is_active=True).first()
                if product is None:
                    raise POSError(f"Unknown SKU '{item.get('sku')}'.")
                lines.append({"product": product, "quantity": item.get("quantity"),
                              "unit_price": item.get("unit_price"), "discount_pct": item.get("discount_pct") or 0})
            sale_date = datetime.date.fromisoformat(payload["sale_date"]) if payload.get("sale_date") else None
            invoice = create_invoice(customer, warehouse, lines, user=None, invoice_date=sale_date,
                                     source="POS", external_ref=str(payload.get("receipt_no", ""))[:60],
                                     notes=f"POS sale via API key {api_key.name}")
            payment_info = payload.get("payment") or {}
            method = payment_info.get("method", Payment.Method.CASH)
            if method not in Payment.Method.values:
                raise POSError(f"Unknown payment method '{method}'.")
            amount = Decimal(str(payment_info.get("amount", invoice.total)))
            if amount > 0:
                record_payment(invoice, min(amount, invoice.total), invoice.invoice_date, method,
                               str(payload.get("receipt_no", "")))
            invoice.refresh_from_db()
            body = {"invoice_id": invoice.pk, "invoice_number": invoice.number, "status": invoice.status,
                    "subtotal": str(invoice.subtotal), "vat_amount": str(invoice.vat_amount),
                    "total": str(invoice.total), "amount_paid": str(invoice.amount_paid),
                    "receipt_no": invoice.external_ref}
            record.status_code, record.response, record.invoice = 201, body, invoice
            record.save(update_fields=["status_code", "response", "invoice"])
            return 201, body, False
    except (SalesError, InsufficientStock) as exc:
        raise POSError(str(exc), 409 if isinstance(exc, InsufficientStock) else 400)
    except (TypeError, ValueError, ArithmeticError) as exc:
        if isinstance(exc, POSError):
            raise
        raise POSError(f"Invalid request: {exc}")
    except IntegrityError:
        # A concurrent request with the same key won the race; return its stored response.
        record = IdempotencyRecord.objects.get(api_key=api_key, key=idempotency_key)
        return record.status_code, record.response, True
