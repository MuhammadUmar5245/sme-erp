"""Load the Al Wadi Trading & Distribution demo dataset (deterministic, random seed 42).

    python manage.py seed_demo --reset          # wipe the database and load 18 months of data
    python manage.py seed_demo --reset --invoices 1500 --months 6   # smaller, faster dataset
"""
import time

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from core.seed import catalog
from core.seed.generator import DemoSeeder
from sales.models import Invoice


class Command(BaseCommand):
    help = "Reset the database and load realistic demo data for Al Wadi Trading & Distribution LLC."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete ALL data before seeding (required if data exists)")
        parser.add_argument("--months", type=int, default=18)
        parser.add_argument("--invoices", type=int, default=8000)
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, reset, months, invoices, seed, **options):
        if Invoice.objects.exists() and not reset:
            raise CommandError("The database already contains data. Re-run with --reset to wipe and reload it.")
        started = time.monotonic()
        if reset:
            self.stdout.write("Resetting database (flush) ...")
            call_command("flush", interactive=False, verbosity=0)
        seeder = DemoSeeder(months=months, target_invoices=invoices, seed=seed, log=self.stdout.write)
        summary = seeder.run()

        self.stdout.write(self.style.SUCCESS(f"\nDemo data loaded in {time.monotonic() - started:.0f} s\n"))
        width = max(len(k) for k in summary)
        for key, value in summary.items():
            self.stdout.write(f"  {key.ljust(width)}  {value}")
        self.stdout.write("\nDemo logins (password for all: %s)" % catalog.DEMO_PASSWORD)
        for email, first, last, role, _d, _j in catalog.DEMO_USERS:
            note = "  (2FA enrolment on first login)" if role in ("Admin", "Accountant") else ""
            self.stdout.write(f"  {role:<13} {email}{note}")
        self.stdout.write(f"\nPower BI API token (user powerbi@alwadi.om): {seeder.powerbi_token}")
        self.stdout.write(f"POS API key (Muscat showroom POS 1):         {seeder.pos_api_key}")
        self.stdout.write("Store these now - the POS key is shown only once.")
