from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import AuditLog
from .roles import ROLES

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=ROLES), source="role_names", required=False
    )
    password = serializers.CharField(write_only=True, required=False, min_length=12)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "phone", "department", "is_active",
                  "roles", "password", "date_joined", "last_login"]
        read_only_fields = ["date_joined", "last_login"]

    def create(self, validated):
        roles = validated.pop("role_names", [])
        password = validated.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": "Required for new users."})
        return services.create_user(password=password, roles=roles, **validated)

    def update(self, instance, validated):
        roles = validated.pop("role_names", None)
        password = validated.pop("password", None)
        for key, value in validated.items():
            setattr(instance, key, value)
        if password:
            from django.contrib.auth.password_validation import validate_password

            validate_password(password, instance)
            instance.set_password(password)
        instance.save()
        if roles is not None:
            services.set_roles(instance, roles)
        return instance


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.prefetch_related("groups").order_by("email")
    serializer_class = UserSerializer
    search_fields = ["email", "first_name", "last_name"]
    filterset_fields = ["is_active", "department"]


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = "__all__"


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    filterset_fields = ["action", "model", "user", "object_id"]
    search_fields = ["user_email", "object_repr"]


class TokenRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    otp = serializers.CharField(required=False, allow_blank=True, help_text="TOTP code if 2FA is enabled")


class ObtainTokenView(APIView):
    """Exchange email + password (+ TOTP code when 2FA applies) for an API token."""

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = TokenRequestSerializer

    def post(self, request):
        data = TokenRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = authenticate(request._request, username=data.validated_data["email"],
                            password=data.validated_data["password"])
        if user is None:
            return Response({"detail": "Invalid credentials or account locked."}, status=status.HTTP_400_BAD_REQUEST)
        if services.has_two_factor(user):
            otp = data.validated_data.get("otp", "").strip()
            # Only check a supplied code: each failed check throttles the device (django-otp).
            if not otp or services.verify_user_token(user, otp) is None:
                return Response({"detail": "Valid TOTP code required."}, status=status.HTTP_400_BAD_REQUEST)
        elif user.requires_2fa:
            return Response({"detail": "Enrol two-factor authentication in the web app first."},
                            status=status.HTTP_403_FORBIDDEN)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key})
