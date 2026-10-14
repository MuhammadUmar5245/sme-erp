#!/bin/sh
# Container start-up: wait for PostgreSQL, apply migrations, collect static files, run gunicorn.
set -e
python scripts/wait_for_db.py
python manage.py migrate --noinput
python manage.py collectstatic --noinput -v 0
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout 120 \
    --access-logfile - \
    ${GUNICORN_EXTRA_ARGS:-}
