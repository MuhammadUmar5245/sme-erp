"""Order-to-cash: sales order -> invoice (stock OUT + journal) -> payment -> credit note.

Invoice posting is a single transaction: products are locked, stock is checked in the invoice's
warehouse (the invoice is blocked if stock is insufficient), then the invoice, stock movements and
the balanced journal entry are written together.
"""
import datetime
from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.money import D, q3, vat_amount
from core.numbering import next_number
from finance import chart
from finance import services as finance
from finance.models import JournalEntry
from inventory import services as inventory
from inventory.models import StockMovement

from .models import CreditNote, CreditNoteLine, Invoice, InvoiceLine, Payment, SalesOrder, SalesOrderLine

ZERO = Decimal("0.000")


class SalesError(ValueError):
    pass


def _line_amounts(quantity, unit_price, discount_pct, vat_rate):
    net = q3(q3(quantity * unit_price) * (100 - discount_pct) / 100)
    vat = vat_amount(net, vat_rate)
    return net, vat, net + vat


def _normalise_lines(lines):
    result = []
    for line in lines:
        product = line["product"]
        quantity = D(line["quantity"])
        if quantity <= 0:
            raise SalesError("Quantities must be positive.")
        unit_price = q3(line["unit_price"]) if line.get("unit_price") not in (None, "") else product.sale_price
        discount = D(line.get("discount_pct") or 0)
        if not (0 <= discount <= 100):
            raise SalesError("Discount must be between 0 and 100%.")
        vat_rate = D(line["vat_rate"]) if line.get("vat_rate") not in (None, "") else product.vat_rate
        result.append({"product": product, "quantity": quantity, "unit_price": unit_price,
                       "discount_pct": discount, "vat_rate": vat_rate, "description": line.get("description", "")})
    if not result:
        raise SalesError("At least one line is required.")
    return result


# ---- Sales orders ----------------------------------------------------------------------------


def recalculate_order(order):
    subtotal = vat = ZERO
    for line in order.lines.all():
        net, line_vat, _ = _line_amounts(line.quantity, line.unit_price, line.discount_pct, line.vat_rate)
        subtotal += net
        vat += line_vat
    order.subtotal, order.vat_amount, order.total = subtotal, vat, subtotal + vat
    order.save(update_fields=["subtotal", "vat_amount", "total", "updated_at"])
    return order


@transaction.atomic
def create_sales_order(customer, warehouse, lines, user=None, order_date=None, delivery_date=None, notes=""):
    order_date = order_date or timezone.localdate()
    order = SalesOrder.objects.create(
        number=next_number("SO", order_date), customer=customer, warehouse=warehouse, order_date=order_date,
        delivery_date=delivery_date, notes=notes, salesperson=user, created_by=user,
    )
    for line in _normalise_lines(lines):
        SalesOrderLine.objects.create(order=order, product=line["product"], quantity=line["quantity"],
                                      unit_price=line["unit_price"], discount_pct=line["discount_pct"],
                                      vat_rate=line["vat_rate"])
    return recalculate_order(order)


@transaction.atomic
def update_sales_order(order, customer, warehouse, lines, delivery_date=None, notes=""):
    """Edit a draft order: header fields and a full replacement of its lines."""
    order = SalesOrder.objects.select_for_update().get(pk=order.pk)
    if order.status != SalesOrder.Status.DRAFT:
        raise SalesError("Only draft sales orders can be edited.")
    normalised = _normalise_lines(lines)
    order.customer, order.warehouse, order.delivery_date, order.notes = customer, warehouse, delivery_date, notes
    order.save()
    order.lines.all().delete()
    for line in normalised:
        SalesOrderLine.objects.create(order=order, product=line["product"], quantity=line["quantity"],
                                      unit_price=line["unit_price"], discount_pct=line["discount_pct"],
                                      vat_rate=line["vat_rate"])
    return recalculate_order(order)


@transaction.atomic
def confirm_sales_order(order, user=None):
    order = SalesOrder.objects.select_for_update().get(pk=order.pk)
    if order.status != SalesOrder.Status.DRAFT:
        raise SalesError("Only draft orders can be confirmed.")
    order.status = SalesOrder.Status.CONFIRMED
    order.save(update_fields=["status", "updated_at"])
    return order


@transaction.atomic
def cancel_sales_order(order, user=None):
    order = SalesOrder.objects.select_for_update().get(pk=order.pk)
    if order.status in (SalesOrder.Status.INVOICED, SalesOrder.Status.CANCELLED):
        raise SalesError("Invoiced or cancelled orders cannot be cancelled.")
    order.status = SalesOrder.Status.CANCELLED
    order.save(update_fields=["status", "updated_at"])
    return order


@transaction.atomic
def invoice_sales_order(order, user=None, invoice_date=None):
    order = SalesOrder.objects.select_for_update().get(pk=order.pk)
    if order.status != SalesOrder.Status.CONFIRMED:
        raise SalesError("Only confirmed orders can be invoiced.")
    lines = [{"product": l.product, "quantity": l.quantity, "unit_price": l.unit_price,
              "discount_pct": l.discount_pct, "vat_rate": l.vat_rate} for l in order.lines.select_related("product")]
    invoice = create_invoice(order.customer, order.warehouse, lines, user=user, invoice_date=invoice_date,
                             sales_order=order, source=Invoice.Source.SALES_ORDER)
    order.status = SalesOrder.Status.INVOICED
    order.save(update_fields=["status", "updated_at"])
    return invoice


# ---- Invoices --------------------------------------------------------------------------------


@transaction.atomic
def create_invoice(customer, warehouse, lines, user=None, invoice_date=None, due_date=None, sales_order=None,
                   source=Invoice.Source.MANUAL, external_ref="", notes="", salesperson=None):
    """Post a tax invoice with 5% VAT per line.

    Writes: sales_invoice + lines, inventory_stockmovement (OUT, one per line) and a journal entry
    Dr AR / Cr Sales / Cr VAT output and Dr COGS / Cr Inventory. Raises InsufficientStock if any line
    cannot be fulfilled from the warehouse.
    """
    if not customer.is_active:
        raise SalesError("Customer is inactive.")
    lines = _normalise_lines(lines)
    invoice_date = invoice_date or timezone.localdate()

    # Lock products, then check stock for the whole invoice (blocks if insufficient).
    locked = inventory.lock_products([line["product"].pk for line in lines])
    needed = defaultdict(Decimal)
    for line in lines:
        line["product"] = locked[line["product"].pk]
        needed[line["product"]] += line["quantity"]
    inventory.check_availability(warehouse, needed)

    invoice = Invoice.objects.create(
        number=next_number("INV", invoice_date), customer=customer, warehouse=warehouse, sales_order=sales_order,
        invoice_date=invoice_date,
        due_date=due_date or invoice_date + datetime.timedelta(days=customer.payment_terms_days),
        source=source, external_ref=external_ref, notes=notes, salesperson=salesperson or user, created_by=user,
    )
    moment = timezone.make_aware(datetime.datetime.combine(invoice_date, datetime.time(12, 0)))
    subtotal = vat = cost = ZERO
    invoice_lines = []
    for line in lines:
        product = line["product"]
        net, line_vat, total = _line_amounts(line["quantity"], line["unit_price"], line["discount_pct"],
                                             line["vat_rate"])
        invoice_lines.append(InvoiceLine(
            invoice=invoice, product=product, description=line["description"] or product.name,
            quantity=line["quantity"], unit_price=line["unit_price"], discount_pct=line["discount_pct"],
            vat_rate=line["vat_rate"], line_subtotal=net, line_vat=line_vat, line_total=total,
            unit_cost=product.cost_price,
        ))
        StockMovement.objects.create(
            product=product, warehouse=warehouse, movement_type=StockMovement.Type.OUT,
            quantity=-line["quantity"], unit_cost=product.cost_price,
            reference_type=StockMovement.Reference.INVOICE, reference_id=invoice.pk, reference_no=invoice.number,
            movement_date=moment, created_by=user,
        )
        subtotal += net
        vat += line_vat
        cost += q3(line["quantity"] * product.cost_price)
    InvoiceLine.objects.bulk_create(invoice_lines)

    invoice.subtotal, invoice.vat_amount, invoice.total, invoice.cost_total = subtotal, vat, subtotal + vat, cost
    invoice.journal_entry = finance.post_journal(
        invoice_date, f"Invoice {invoice.number} - {customer.name}",
        [
            (chart.ACCOUNTS_RECEIVABLE, subtotal + vat, 0, customer.name),
            (chart.SALES, 0, subtotal),
            (chart.VAT_OUTPUT, 0, vat, "VAT 5%"),
            (chart.COGS, cost, 0),
            (chart.INVENTORY, 0, cost),
        ],
        JournalEntry.Source.INVOICE, invoice.pk, invoice.number, user,
    )
    invoice.save(update_fields=["subtotal", "vat_amount", "total", "cost_total", "journal_entry"])
    return invoice


def _refresh_status(invoice):
    if invoice.status == Invoice.Status.CANCELLED:
        return
    if invoice.balance_due <= 0:
        invoice.status = Invoice.Status.PAID
    elif invoice.amount_paid > 0 or invoice.amount_credited > 0:
        invoice.status = Invoice.Status.PARTIAL
    else:
        invoice.status = Invoice.Status.POSTED


@transaction.atomic
def record_payment(invoice, amount, payment_date=None, method=Payment.Method.BANK, reference="", user=None):
    """Customer payment (partial payments allowed): Dr Cash/Bank / Cr Accounts receivable."""
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    amount = q3(amount)
    if invoice.status == Invoice.Status.CANCELLED:
        raise SalesError("Cannot record a payment on a cancelled invoice.")
    if amount <= 0:
        raise SalesError("Payment amount must be positive.")
    if amount > invoice.balance_due:
        raise SalesError(f"Payment {amount} exceeds the balance due {invoice.balance_due}.")
    payment_date = payment_date or timezone.localdate()
    payment = Payment.objects.create(
        number=next_number("RCPT", payment_date), invoice=invoice, customer=invoice.customer,
        payment_date=payment_date, amount=amount, method=method, reference=reference, created_by=user,
    )
    debit_account = chart.CASH if method == Payment.Method.CASH else chart.BANK
    payment.journal_entry = finance.post_journal(
        payment_date, f"Receipt {payment.number} from {invoice.customer.name} for {invoice.number}",
        [(debit_account, amount, 0), (chart.ACCOUNTS_RECEIVABLE, 0, amount, invoice.customer.name)],
        JournalEntry.Source.PAYMENT, payment.pk, reference or invoice.number, user,
    )
    payment.save(update_fields=["journal_entry"])
    invoice.amount_paid += amount
    _refresh_status(invoice)
    invoice.save(update_fields=["amount_paid", "status", "updated_at"])
    return payment


@transaction.atomic
def create_credit_note(invoice, lines, reason, credit_date=None, restock=True, user=None):
    """Credit note for returned/disputed goods.

    lines: [{"invoice_line": InvoiceLine, "quantity": n}]. Reverses revenue and VAT against AR and,
    when restock=True, returns goods to stock at their original cost (Dr Inventory / Cr COGS).
    """
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if invoice.status == Invoice.Status.CANCELLED:
        raise SalesError("Cannot credit a cancelled invoice.")
    if not lines:
        raise SalesError("Select at least one line to credit.")
    credit_date = credit_date or timezone.localdate()
    note = CreditNote.objects.create(
        number=next_number("CN", credit_date), invoice=invoice, customer=invoice.customer, credit_date=credit_date,
        reason=reason, restock=restock, created_by=user,
    )
    moment = timezone.make_aware(datetime.datetime.combine(credit_date, datetime.time(15, 0)))
    subtotal = vat = cost = ZERO
    for item in lines:
        inv_line = item["invoice_line"]
        quantity = D(item["quantity"])
        if inv_line.invoice_id != invoice.pk:
            raise SalesError("Credit line does not belong to this invoice.")
        already = sum((cl.quantity for cl in inv_line.credit_lines.all()), ZERO)
        if quantity <= 0 or quantity > inv_line.quantity - already:
            raise SalesError(f"{inv_line.product.sku}: can credit at most {inv_line.quantity - already}.")
        unit_net = q3(inv_line.line_subtotal / inv_line.quantity)
        net = q3(unit_net * quantity) if quantity != inv_line.quantity else inv_line.line_subtotal
        line_vat = vat_amount(net, inv_line.vat_rate)
        CreditNoteLine.objects.create(
            credit_note=note, invoice_line=inv_line, product=inv_line.product, quantity=quantity,
            unit_price=unit_net, vat_rate=inv_line.vat_rate, line_subtotal=net, line_vat=line_vat,
            line_total=net + line_vat, unit_cost=inv_line.unit_cost,
        )
        if restock:
            StockMovement.objects.create(
                product=inv_line.product, warehouse=invoice.warehouse, movement_type=StockMovement.Type.IN,
                quantity=quantity, unit_cost=inv_line.unit_cost, reference_type=StockMovement.Reference.CREDIT_NOTE,
                reference_id=note.pk, reference_no=note.number, movement_date=moment, created_by=user,
                note=f"Return on {invoice.number}",
            )
            cost += q3(quantity * inv_line.unit_cost)
        subtotal += net
        vat += line_vat

    note.subtotal, note.vat_amount, note.total, note.cost_total = subtotal, vat, subtotal + vat, cost
    journal_lines = [
        (chart.SALES_RETURNS, subtotal, 0, reason),
        (chart.VAT_OUTPUT, vat, 0, "VAT 5% reversal"),
        (chart.ACCOUNTS_RECEIVABLE, 0, subtotal + vat, invoice.customer.name),
    ]
    if cost:
        journal_lines += [(chart.INVENTORY, cost, 0), (chart.COGS, 0, cost)]
    note.journal_entry = finance.post_journal(
        credit_date, f"Credit note {note.number} on {invoice.number}", journal_lines,
        JournalEntry.Source.CREDIT_NOTE, note.pk, note.number, user,
    )
    note.save(update_fields=["subtotal", "vat_amount", "total", "cost_total", "journal_entry"])
    invoice.amount_credited += note.total
    _refresh_status(invoice)
    invoice.save(update_fields=["amount_credited", "status", "updated_at"])
    return note


def customer_outstanding(customer):
    total = ZERO
    for invoice in customer.invoices.exclude(status__in=[Invoice.Status.CANCELLED, Invoice.Status.PAID]):
        total += invoice.balance_due
    return total
