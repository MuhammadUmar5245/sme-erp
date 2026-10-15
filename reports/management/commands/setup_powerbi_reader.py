"""(Re)create the reporting views and the read-only `powerbi_reader` PostgreSQL role.

Usage: python manage.py setup_powerbi_reader [--password <pw>] [--views-only]
The password defaults to POWERBI_READER_PASSWORD from .env. Use it to rotate the password.
"""
import os

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from reports.reporting_sql import create_powerbi_reader, rebuild_views


class Command(BaseCommand):
    help = "Rebuild schema 'reporting' and create/update the read-only role powerbi_reader."

    def add_arguments(self, parser):
        parser.add_argument("--password", default=os.environ.get("POWERBI_READER_PASSWORD", ""))
        parser.add_argument("--views-only", action="store_true")

    def handle(self, *args, password, views_only, **options):
        with transaction.atomic(), connection.cursor() as cursor:
            rebuild_views(cursor)
            self.stdout.write(self.style.SUCCESS("Schema 'reporting' rebuilt."))
            if views_only:
                return
            if not password:
                raise CommandError("No password: set POWERBI_READER_PASSWORD or pass --password.")
            create_powerbi_reader(cursor, password)
        self.stdout.write(self.style.SUCCESS("Role 'powerbi_reader' ready (SELECT on schema reporting only)."))
