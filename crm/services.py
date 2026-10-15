"""CRM business logic: interactions, feedback (CSAT 1-5) and the Customer 360 view."""
from decimal import Decimal

from django.db.models import Avg, Count, Max, Sum
from django.utils import timezone

from core.numbering import next_number

from .models import Customer, Feedback, Interaction


def next_customer_code():
    return next_number("CUS").replace("CUS-", "C")


def log_interaction(customer, interaction_type, subject, notes="", user=None, interaction_date=None,
                    follow_up_date=None):
    status = Interaction.Status.OPEN if interaction_type == Interaction.Type.COMPLAINT else Interaction.Status.CLOSED
    return Interaction.objects.create(
        customer=customer, interaction_type=interaction_type, subject=subject, notes=notes, user=user,
        interaction_date=interaction_date or timezone.now(), follow_up_date=follow_up_date, status=status,
        created_by=user,
    )


def close_interaction(interaction, user=None):
    interaction.status = Interaction.Status.CLOSED
    interaction.save(update_fields=["status", "updated_at"])
    return interaction


def record_feedback(customer, score, comment="", channel=Feedback.Channel.SURVEY, invoice=None, feedback_date=None,
                    user=None):
    score = int(score)
    if not 1 <= score <= 5:
        raise ValueError("Satisfaction score must be between 1 and 5.")
    if invoice is not None and invoice.customer_id != customer.pk:
        raise ValueError("Invoice belongs to another customer.")
    return Feedback.objects.create(customer=customer, score=score, comment=comment, channel=channel, invoice=invoice,
                                   feedback_date=feedback_date or timezone.localdate(), created_by=user)


def average_csat(queryset=None):
    queryset = queryset if queryset is not None else Feedback.objects.all()
    value = queryset.aggregate(avg=Avg("score"))["avg"]
    return Decimal(str(round(value, 2))) if value is not None else None


def customer_360(customer):
    """Everything about one customer: orders, invoices, balance, interactions, satisfaction."""
    from sales.models import Invoice
    from sales.services import customer_outstanding

    invoices = customer.invoices.exclude(status=Invoice.Status.CANCELLED)
    stats = invoices.aggregate(revenue=Sum("subtotal"), count=Count("id"), last=Max("invoice_date"))
    overdue = [inv for inv in invoices.exclude(status=Invoice.Status.PAID) if inv.is_overdue]
    feedback = customer.feedback.all()
    return {
        "customer": customer,
        "contacts": customer.contacts.all(),
        "orders": customer.sales_orders.order_by("-order_date")[:10],
        "invoices": invoices.order_by("-invoice_date")[:10],
        "payments": customer.payments.order_by("-payment_date")[:10],
        "interactions": customer.interactions.select_related("user")[:15],
        "feedback": feedback[:10],
        "total_revenue": stats["revenue"] or Decimal("0"),
        "invoice_count": stats["count"],
        "last_purchase": stats["last"],
        "outstanding": customer_outstanding(customer),
        "overdue_amount": sum((inv.balance_due for inv in overdue), Decimal("0")),
        "overdue_count": len(overdue),
        "avg_csat": average_csat(feedback),
        "feedback_count": feedback.count(),
        "open_complaints": customer.interactions.filter(
            interaction_type=Interaction.Type.COMPLAINT, status=Interaction.Status.OPEN).count(),
        "credit_available": customer.credit_limit - customer_outstanding(customer) if customer.credit_limit else None,
    }


def active_customers():
    return Customer.objects.filter(is_active=True)
