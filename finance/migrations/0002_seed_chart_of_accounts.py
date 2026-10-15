"""Data migration: seed the standard chart of accounts used by automatic postings."""
from django.db import migrations


def seed(apps, schema_editor):
    from finance.chart import CHART_OF_ACCOUNTS

    Account = apps.get_model("finance", "Account")
    for code, name, account_type, system in CHART_OF_ACCOUNTS:
        Account.objects.get_or_create(code=code, defaults={"name": name, "account_type": account_type,
                                                           "is_system": system})


def unseed(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("finance", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
