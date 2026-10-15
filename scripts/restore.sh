#!/bin/bash
# Restore the SME-ERP database from a backup made by backup.sh (see docs/disaster_recovery.md).
#
#   restore.sh                      # list available backups
#   restore.sh latest               # restore the newest backup
#   restore.sh sme_erp_20261014_020000.dump[.enc] [--yes]
#
# Stop the web container first (make restore does this) so no sessions write during the restore.
set -Eeuo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
export PGPASSWORD="${POSTGRES_PASSWORD}"

if [ $# -eq 0 ]; then
    echo "Available backups in ${BACKUP_DIR}:"
    ls -1t "${BACKUP_DIR}"/sme_erp_*.dump* 2>/dev/null | grep -v '\.sha256$' || echo "  (none)"
    echo "Usage: $0 <file|latest> [--yes]"
    exit 1
fi

TARGET="$1"
if [ "${TARGET}" = "latest" ]; then
    TARGET="$(ls -1t "${BACKUP_DIR}"/sme_erp_*.dump* 2>/dev/null | grep -v '\.sha256$' | head -n1 || true)"
    [ -n "${TARGET}" ] || { echo "No backups found." >&2; exit 1; }
elif [ ! -f "${TARGET}" ]; then
    TARGET="${BACKUP_DIR}/${TARGET}"
fi
[ -f "${TARGET}" ] || { echo "Backup file not found: ${TARGET}" >&2; exit 1; }

# Integrity check against the stored checksum.
if [ -f "${TARGET}.sha256" ]; then
    ( cd "$(dirname "${TARGET}")" && sha256sum --check --status "$(basename "${TARGET}").sha256" ) \
        || { echo "Checksum mismatch - backup is corrupt." >&2; exit 2; }
    echo "Checksum OK."
fi

echo "This will REPLACE all data in database '${POSTGRES_DB}' on '${POSTGRES_HOST}' with:"
echo "  $(basename "${TARGET}")"
if [ "${2:-}" != "--yes" ] && [ "${RESTORE_CONFIRM:-}" != "yes" ]; then
    read -r -p "Type RESTORE to continue: " answer
    [ "${answer}" = "RESTORE" ] || { echo "Cancelled."; exit 1; }
fi

WORK="${TARGET}"
if [[ "${TARGET}" == *.enc ]]; then
    [ -n "${BACKUP_ENCRYPTION_KEY:-}" ] || { echo "BACKUP_ENCRYPTION_KEY is required to decrypt." >&2; exit 1; }
    WORK="$(mktemp /tmp/restore.XXXXXX.dump)"
    openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass env:BACKUP_ENCRYPTION_KEY -in "${TARGET}" -out "${WORK}"
fi

START="$(date +%s)"
echo "[$(date -Iseconds)] Restoring ..."
pg_restore --host "${POSTGRES_HOST}" --port "${POSTGRES_PORT:-5432}" --username "${POSTGRES_USER}" \
    --dbname "${POSTGRES_DB}" --clean --if-exists --no-owner --single-transaction --exit-on-error "${WORK}"
[ "${WORK}" != "${TARGET}" ] && rm -f "${WORK}"

INVOICES="$(psql --host "${POSTGRES_HOST}" --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" -tAc \
    'SELECT COUNT(*) FROM sales_invoice')"
echo "[$(date -Iseconds)] Restore finished in $(( $(date +%s) - START )) s. Invoices in database: ${INVOICES}"
echo "Start the application again (make up) and check https://localhost/health/"
