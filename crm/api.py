from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import services
from .models import Contact, Customer, Feedback, Interaction


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "code", "name", "customer_type", "phone", "email", "city", "address", "vat_number",
                  "credit_limit", "payment_terms_days", "is_active", "notes"]


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ["id", "customer", "name", "position", "phone", "email", "is_primary"]


class InteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interaction
        fields = ["id", "customer", "interaction_type", "interaction_date", "subject", "notes", "status",
                  "follow_up_date", "user"]
        read_only_fields = ["user"]

    def create(self, data):
        data["user"] = self.context["request"].user
        return super().create(data)


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ["id", "customer", "invoice", "feedback_date", "score", "channel", "comment"]

    def create(self, d):
        try:
            return services.record_feedback(d["customer"], d["score"], d.get("comment", ""),
                                            d.get("channel", Feedback.Channel.SURVEY), d.get("invoice"),
                                            d.get("feedback_date"), self.context["request"].user)
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)})


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    search_fields = ["code", "name", "phone", "email"]
    filterset_fields = ["city", "customer_type", "is_active"]

    @action(detail=True, url_path="360")
    def customer_360(self, request, pk=None):
        data = services.customer_360(self.get_object())
        return Response({
            "customer": CustomerSerializer(data["customer"]).data,
            "total_revenue": data["total_revenue"], "invoice_count": data["invoice_count"],
            "last_purchase": data["last_purchase"], "outstanding": data["outstanding"],
            "overdue_amount": data["overdue_amount"], "avg_csat": data["avg_csat"],
            "feedback_count": data["feedback_count"], "open_complaints": data["open_complaints"],
            "interactions": InteractionSerializer(data["interactions"], many=True).data,
        })


class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    filterset_fields = ["customer"]


class InteractionViewSet(viewsets.ModelViewSet):
    queryset = Interaction.objects.select_related("customer")
    serializer_class = InteractionSerializer
    filterset_fields = ["customer", "interaction_type", "status"]
    search_fields = ["subject", "notes"]


class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.select_related("customer")
    serializer_class = FeedbackSerializer
    filterset_fields = ["customer", "score", "channel"]
