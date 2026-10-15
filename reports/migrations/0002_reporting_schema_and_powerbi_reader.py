"""Create the PostgreSQL `reporting` schema (star-schema views) and the read-only role `powerbi_reader`.

The role's password comes from POWERBI_READER_PASSWORD in .env; without it the role is not created
(run `python manage.py setup_powerbi_reader` later).
"""
import os

from django.db import migrations


def forwards(apps, schema_editor):
    from reports.reporting_sql import create_powerbi_reader, rebuild_views

    with schema_editor.connection.cursor() as cursor:
        rebuild_views(cursor)
        create_powerbi_reader(cursor, os.environ.get("POWERBI_READER_PASSWORD", ""))


def backwards(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA IF EXISTS reporting CASCADE")


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0001_initial"),
        ("inventory", "0001_initial"),
        ("purchasing", "0001_initial"),
        ("sales", "0001_initial"),
        ("crm", "0002_initial"),
        ("finance", "0002_seed_chart_of_accounts"),
        ("hr", "0002_employee_leaverequest"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
