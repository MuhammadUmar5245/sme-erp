"""Block until PostgreSQL accepts connections (used by the web container on start-up)."""
import os
import sys
import time

import psycopg

params = {
    "dbname": os.environ.get("POSTGRES_DB", "sme_erp"),
    "user": os.environ.get("POSTGRES_USER", "sme_erp"),
    "password": os.environ.get("POSTGRES_PASSWORD", ""),
    "host": os.environ.get("POSTGRES_HOST", "db"),
    "port": os.environ.get("POSTGRES_PORT", "5432"),
}

for attempt in range(60):
    try:
        psycopg.connect(**params, connect_timeout=2).close()
        print("Database is ready.")
        sys.exit(0)
    except psycopg.OperationalError:
        time.sleep(1)
print("Database not reachable after 60 seconds.", file=sys.stderr)
sys.exit(1)
