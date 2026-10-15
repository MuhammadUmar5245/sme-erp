from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _sync_roles(sender, using="default", **kwargs):
    from .services import sync_role_permissions

    sync_role_permissions(using=using)


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Accounts and security"

    def ready(self):
        from . import audit

        audit.connect()
        # Re-apply role permissions after every migrate so new modules' permissions are granted.
        post_migrate.connect(_sync_roles, dispatch_uid="accounts_sync_roles")
