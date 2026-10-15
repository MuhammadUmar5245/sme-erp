"""Procure-to-pay: purchase order -> approval -> goods receipt -> supplier bill -> supplier payment.

Cross-module postings (stock IN + journal entries) run inside transaction.atomic().
"""
import datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.money import D, q3
from core.numbering import next_number
from finance import chart
from finance import services as finance
from finance.models import JournalEntry
from inventory import services as inventory
from inventory.models import StockMovement

from .models import GoodsReceipt, GoodsReceiptLine, PurchaseOrder, PurchaseOrderLine, SupplierBill, SupplierPayment


class PurchasingError(ValueError):
    pass


def recalculate_totals(order):
    lines = list(order.lines.all())
    order.subtotal = sum((line.line_subtotal for line in lines), Decimal("0"))
    order.vat_amount = sum((line.line_vat for line in lines), Decimal("0"))
    order.total = order.subtotal + order.vat_amount
    order.save(update_fields=["subtotal", "vat_amount", "total", "updated_at"])
    return order


@transaction.atomic
def create_purchase_order(supplier, warehouse, lines, user=None, order_date=None, expected_date=None, notes=""):
    """lines: [{"product": Product, "quantity": n, "unit_cost": x (default product cost), "vat_rate": 5}]"""
    if not lines:
        raise PurchasingError("A purchase order needs at least one line.")
    order_date = order_date or timezone.localdate()
    order = PurchaseOrder.objects.create(
        number=next_number("PO", order_date), supplier=supplier, warehouse=warehouse, order_date=order_date,
        expected_date=expected_date, notes=notes, created_by=user,
    )
    for line in lines:
        quantity = D(line["quantity"])
        if quantity <= 0:
            raise PurchasingError("Quantities must be positive.")
        product = line["product"]
        PurchaseOrderLine.objects.create(
            order=order, product=product, quantity=quantity,
            unit_cost=q3(line.get("unit_cost") if line.get("unit_cost") is not None else product.cost_price),
            vat_rate=D(line.get("vat_rate", product.vat_rate)),
        )
    return recalculate_totals(order)


@transaction.atomic
def update_purchase_order(order, supplier, warehouse, lines, expected_date=None, notes=""):
    """Edit a draft order: header fields and a full replacement of its lines."""
    order = PurchaseOrder.objects.select_for_update().get(pk=order.pk)
    if order.status != PurchaseOrder.Status.DRAFT:
        raise PurchasingError("Only draft purchase orders can be edited.")
    if not lines:
        raise PurchasingError("A purchase order needs at least one line.")
    order.supplier, order.warehouse, order.expected_date, order.notes = supplier, warehouse, expected_date, notes
    order.save()
    order.lines.all().delete()
    for line in lines:
        if D(line["quantity"]) <= 0:
            raise PurchasingError("Quantities must be positive.")
        product = line["product"]
        PurchaseOrderLine.objects.create(
            order=order, product=product, quantity=D(line["quantity"]),
            unit_cost=q3(line.get("unit_cost") if line.get("unit_cost") is not None else product.cost_price),
            vat_rate=D(line.get("vat_rate") if line.get("vat_rate") is not None else product.vat_rate),
        )
    return recalculate_totals(order)


@transaction.atomic
def approve_purchase_order(order, user=None):
    order = PurchaseOrder.objects.select_for_update().get(pk=order.pk)
    if order.status != PurchaseOrder.Status.DRAFT:
        raise PurchasingError(f"Only draft orders can be approved (status is {order.get_status_display()}).")
    order.status = PurchaseOrder.Status.APPROVED
    order.approved_by = user
    order.approved_at = timezone.now()
    order.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    return order


@transaction.atomic
def cancel_purchase_order(order, user=None):
    order = PurchaseOrder.objects.select_for_update().get(pk=order.pk)
    if order.status not in (PurchaseOrder.Status.DRAFT, PurchaseOrder.Status.APPROVED) or order.receipts.exists():
        raise PurchasingError("Only draft or approved orders without receipts can be cancelled.")
    order.status = PurchaseOrder.Status.CANCELLED
    order.save(update_fields=["status", "updated_at"])
    return order


@transaction.atomic
def receive_goods(order, quantities=None, user=None, receipt_date=None, notes=""):
    """Goods receipt: stock IN for each line + journal Dr Inventory / Cr GRNI.

    quantities: {po_line_id: qty}; None receives everything still outstanding. Partial receipts are allowed;
    the order becomes RECEIVED once every line is fully received.
    """
    order = PurchaseOrder.objects.select_for_update().get(pk=order.pk)
    if order.status != PurchaseOrder.Status.APPROVED:
        raise PurchasingError("Goods can only be received against an approved purchase order.")
    receipt_date = receipt_date or timezone.localdate()
    po_lines = {line.pk: line for line in order.lines.select_related("product")}
    if quantities is None:
        quantities = {pk: line.remaining_quantity for pk, line in po_lines.items()}
    quantities = {int(pk): D(qty) for pk, qty in quantities.items() if D(qty) > 0}
    if not quantities:
        raise PurchasingError("Nothing to receive.")

    receipt = GoodsReceipt.objects.create(
        number=next_number("GRN", receipt_date), purchase_order=order, warehouse=order.warehouse,
        receipt_date=receipt_date, notes=notes, created_by=user,
    )
    moment = timezone.make_aware(datetime.datetime.combine(receipt_date, datetime.time(9, 0)))
    total_value = Decimal("0")
    for pk, qty in quantities.items():
        line = po_lines.get(pk)
        if line is None:
            raise PurchasingError(f"Line {pk} does not belong to {order.number}.")
        if qty > line.remaining_quantity:
            raise PurchasingError(f"{line.product.sku}: receiving {qty} exceeds outstanding {line.remaining_quantity}.")
        GoodsReceiptLine.objects.create(receipt=receipt, po_line=line, product=line.product, quantity=qty,
                                        unit_cost=line.unit_cost)
        inventory.receive_stock(line.product, order.warehouse, qty, line.unit_cost,
                                StockMovement.Reference.GOODS_RECEIPT, receipt.pk, receipt.number, user, moment)
        line.received_quantity += qty
        line.save(update_fields=["received_quantity"])
        total_value += q3(qty * line.unit_cost)

    finance.post_journal(receipt_date, f"Goods receipt {receipt.number} for {order.number}",
                         [(chart.INVENTORY, total_value, 0), (chart.GRNI, 0, total_value)],
                         JournalEntry.Source.GOODS_RECEIPT, receipt.pk, receipt.number, user)
    if all(line.received_quantity >= line.quantity for line in po_lines.values()):
        order.status = PurchaseOrder.Status.RECEIVED
        order.save(update_fields=["status", "updated_at"])
    return receipt


@transaction.atomic
def create_bill_from_po(order, supplier_invoice_no, bill_date=None, user=None):
    """Supplier bill for received goods: Dr GRNI + Dr VAT input / Cr Accounts payable."""
    order = PurchaseOrder.objects.select_for_update().get(pk=order.pk)
    if order.status != PurchaseOrder.Status.RECEIVED:
        raise PurchasingError("Only fully received orders can be billed.")
    if order.bills.exclude(status=SupplierBill.Status.CANCELLED).exists():
        raise PurchasingError(f"{order.number} has already been billed.")
    bill_date = bill_date or timezone.localdate()
    subtotal = vat = Decimal("0")
    for line in order.lines.all():
        net = q3(line.received_quantity * line.unit_cost)
        subtotal += net
        vat += q3(net * line.vat_rate / 100)
    bill = SupplierBill.objects.create(
        number=next_number("BILL", bill_date), supplier_invoice_no=supplier_invoice_no, supplier=order.supplier,
        purchase_order=order, bill_date=bill_date,
        due_date=bill_date + datetime.timedelta(days=order.supplier.payment_terms_days),
        subtotal=subtotal, vat_amount=vat, total=subtotal + vat, created_by=user,
    )
    bill.journal_entry = finance.post_journal(
        bill_date, f"Supplier bill {bill.number} {order.supplier.name}",
        [(chart.GRNI, subtotal, 0), (chart.VAT_INPUT, vat, 0), (chart.ACCOUNTS_PAYABLE, 0, subtotal + vat)],
        JournalEntry.Source.SUPPLIER_BILL, bill.pk, supplier_invoice_no, user,
    )
    bill.save(update_fields=["journal_entry"])
    order.status = PurchaseOrder.Status.BILLED
    order.save(update_fields=["status", "updated_at"])
    return bill


@transaction.atomic
def pay_supplier_bill(bill, amount, payment_date=None, method=SupplierPayment.Method.BANK, reference="", user=None):
    """Supplier payment (partial allowed): Dr Accounts payable / Cr Bank or Cash."""
    bill = SupplierBill.objects.select_for_update().get(pk=bill.pk)
    amount = q3(amount)
    if bill.status == SupplierBill.Status.CANCELLED:
        raise PurchasingError("Cannot pay a cancelled bill.")
    if amount <= 0 or amount > bill.balance_due:
        raise PurchasingError(f"Payment must be between 0.001 and the balance due ({bill.balance_due}).")
    payment_date = payment_date or timezone.localdate()
    payment = SupplierPayment.objects.create(
        number=next_number("SPAY", payment_date), bill=bill, supplier=bill.supplier, payment_date=payment_date,
        amount=amount, method=method, reference=reference, created_by=user,
    )
    credit_account = chart.CASH if method == SupplierPayment.Method.CASH else chart.BANK
    payment.journal_entry = finance.post_journal(
        payment_date, f"Payment {payment.number} to {bill.supplier.name} for {bill.number}",
        [(chart.ACCOUNTS_PAYABLE, amount, 0), (credit_account, 0, amount)],
        JournalEntry.Source.SUPPLIER_PAYMENT, payment.pk, reference or bill.number, user,
    )
    payment.save(update_fields=["journal_entry"])
    bill.amount_paid += amount
    bill.status = SupplierBill.Status.PAID if bill.balance_due <= 0 else SupplierBill.Status.PARTIAL
    bill.save(update_fields=["amount_paid", "status", "updated_at"])
    return payment
