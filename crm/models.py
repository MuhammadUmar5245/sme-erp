from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel, money_field

OMAN_CITIES = [
    ("Muscat", "Muscat"),
    ("Seeb", "Seeb"),
    ("Bawshar", "Bawshar"),
    ("Sohar", "Sohar"),
    ("Salalah", "Salalah"),
    ("Nizwa", "Nizwa"),
    ("Sur", "Sur"),
    ("Ibri", "Ibri"),
    ("Barka", "Barka"),
    ("Rustaq", "Rustaq"),
    ("Other", "Other"),
]


class Customer(TimeStampedModel):
    class Type(models.TextChoices):
        RETAIL = "RETAIL", "Retail shop"
        WHOLESALE = "WHOLESALE", "Wholesaler"
        HYPERMARKET = "HYPERMARKET", "Hypermarket / supermarket"
        HORECA = "HORECA", "Hotel / restaurant / cafe"
        INSTITUTION = "INSTITUTION", "Institution"

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150, db_index=True)
    customer_type = models.CharField(max_length=12, choices=Type.choices, default=Type.RETAIL)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    city = models.CharField(max_length=30, choices=OMAN_CITIES, default="Muscat", db_index=True)
    address = models.CharField(max_length=200, blank=True)
    vat_number = models.CharField("VAT number", max_length=20, blank=True)
    credit_limit = money_field()
    payment_terms_days = models.PositiveSmallIntegerField(default=30)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Contact(TimeStampedModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="contacts")
    name = models.CharField(max_length=100)
    position = models.CharField(max_length=80, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "name"]

    def __str__(self):
        return f"{self.name} ({self.customer.name})"


class Interaction(TimeStampedModel):
    class Type(models.TextChoices):
        CALL = "CALL", "Phone call"
        VISIT = "VISIT", "Visit"
        EMAIL = "EMAIL", "E-mail"
        COMPLAINT = "COMPLAINT", "Complaint"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="interactions")
    interaction_type = models.CharField(max_length=10, choices=Type.choices)
    interaction_date = models.DateTimeField(default=timezone.now, db_index=True)
    subject = models.CharField(max_length=150)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=6, choices=Status.choices, default=Status.CLOSED)
    follow_up_date = models.DateField(null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="crm_interactions")

    class Meta:
        ordering = ["-interaction_date"]

    def __str__(self):
        return f"{self.get_interaction_type_display()}: {self.subject}"


class Feedback(TimeStampedModel):
    class Channel(models.TextChoices):
        SURVEY = "SURVEY", "Survey"
        CALL = "CALL", "Phone"
        VISIT = "VISIT", "Visit"
        EMAIL = "EMAIL", "E-mail"
        WHATSAPP = "WHATSAPP", "WhatsApp"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="feedback")
    invoice = models.ForeignKey("sales.Invoice", null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="feedback")
    feedback_date = models.DateField(default=timezone.localdate, db_index=True)
    score = models.PositiveSmallIntegerField(
        "Satisfaction (1-5)", validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.SURVEY)
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-feedback_date", "-id"]
        verbose_name_plural = "feedback"
        constraints = [
            models.CheckConstraint(condition=models.Q(score__gte=1, score__lte=5), name="feedback_score_1_5")
        ]

    def __str__(self):
        return f"{self.customer.name}: {self.score}/5"
