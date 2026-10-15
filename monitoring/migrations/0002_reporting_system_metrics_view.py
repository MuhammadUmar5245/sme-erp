"""Rebuild the reporting schema so it includes reporting.fact_system_metrics_hourly (Power BI System Health)."""
from django.db import migrations


def forwards(apps, schema_editor):
    from reports.reporting_sql import rebuild_views

    with schema_editor.connection.cursor() as cursor:
        rebuild_views(cursor)


class Migration(migrations.Migration):
    dependencies = [
        ("monitoring", "0001_initial"),
        ("reports", "0002_reporting_schema_and_powerbi_reader"),
    ]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
