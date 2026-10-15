from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra)

    def get_by_natural_key(self, username):
        return self.get(**{f"{self.model.USERNAME_FIELD}__iexact": username})


class User(AbstractBaseUser, PermissionsMixin):
    """ERP user. Logs in with e-mail; roles are Django groups."""

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    department = models.ForeignKey(
        "hr.Department", null=True, blank=True, on_delete=models.SET_NULL, related_name="users"
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False, help_text="Can log in to the Django admin site.")
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.get_full_name() or self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name or self.email

    @property
    def role_names(self):
        return [g.name for g in self.groups.all()]

    @property
    def role_list(self):
        return ", ".join(self.role_names)

    @property
    def requires_2fa(self):
        from .roles import MFA_REQUIRED_ROLES

        return self.is_superuser or self.groups.filter(name__in=MFA_REQUIRED_ROLES).exists()


class AuditLog(models.Model):
    """Immutable record of every create/update/delete on business data, plus logins."""

    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        LOGIN = "login", "Login"
        LOGOUT = "logout", "Logout"
        LOGIN_FAILED = "login_failed", "Login failed"

    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs"
    )
    user_email = models.CharField(max_length=254, blank=True)
    action = models.CharField(max_length=20, choices=Action.choices, db_index=True)
    model = models.CharField(max_length=100, db_index=True, help_text="app_label.model")
    object_id = models.CharField(max_length=64, blank=True, db_index=True)
    object_repr = models.CharField(max_length=200, blank=True)
    changes = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-timestamp", "-id"]
        default_permissions = ("view",)
        verbose_name = "audit log entry"
        verbose_name_plural = "audit log"

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} {self.user_email} {self.action} {self.model}#{self.object_id}"
