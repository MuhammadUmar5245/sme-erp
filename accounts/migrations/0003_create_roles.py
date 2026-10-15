"""Data migration: create the 7 role groups (Admin, Manager, Accountant, SalesOfficer, Storekeeper,
HROfficer, Viewer) with their model-level permissions."""
from django.contrib.auth.management import create_permissions
from django.db import migrations


def create_roles(apps, schema_editor):
    # Permissions are normally created after all migrations; create them now so they can be granted.
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    from accounts.services import sync_role_permissions

    sync_role_permissions(using=schema_editor.connection.alias)


def remove_roles(apps, schema_editor):
    from accounts.roles import ROLES

    apps.get_model("auth", "Group").objects.filter(name__in=ROLES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_user_department_auditlog"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [migrations.RunPython(create_roles, remove_roles)]
