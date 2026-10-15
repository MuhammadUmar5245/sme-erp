#!/bin/bash
# SME-ERP database backup (report 5.2.2). Runs daily from the cron container; also `make backup`.
#
#  - pg_dump custom format (compressed), timestamped: /backups/sme_erp_YYYYmmdd_HHMMSS.dump
#  - optional AES-256 encryption at rest when BACKUP_ENCRYPTION_KEY is set (.dump.enc)
#  - SHA-256 checksum file next to each backup
#  - optional off-site copy: Amazon S3 (S3_BUCKET + AWS_* vars) and/or Azure Blob (AZURE_BLOB_SAS_URL)
#  - retention: deletes local backups older than BACKUP_RETENTION_DAYS (default 14)
#  - writes /backups/last_backup.json, shown on the monitoring page and the system-metrics API
set -Eeuo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
STAMP="$(date +%Y%m%d_%H%M%S)"
FILE="${BACKUP_DIR}/sme_erp_${STAMP}.dump"
STATUS_FILE="${BACKUP_DIR}/last_backup.json"
STARTED="$(date -Iseconds)"
START_EPOCH="$(date +%s)"
OFFSITE="none"

mkdir -p "${BACKUP_DIR}"
export PGPASSWORD="${POSTGRES_PASSWORD}"

write_status() {
    local status="$1" message="$2" size=0
    [ -f "${FILE}" ] && size="$(stat -c %s "${FILE}")"
    cat > "${STATUS_FILE}.tmp" <<JSON
{"status": "${status}", "file": "$(basename "${FILE}")", "size_bytes": ${size},
 "started_at": "${STARTED}", "finished_at": "$(date -Iseconds)",
 "duration_seconds": $(( $(date +%s) - START_EPOCH )), "offsite": "${OFFSITE}",
 "retention_days": ${RETENTION_DAYS}, "message": "${message}"}
JSON
    mv "${STATUS_FILE}.tmp" "${STATUS_FILE}"
}
trap 'write_status "failed" "Backup failed at line ${LINENO}"; echo "Backup FAILED" >&2' ERR

echo "[$(date -Iseconds)] Backing up database ${POSTGRES_DB} on ${POSTGRES_HOST} ..."
pg_dump --host "${POSTGRES_HOST}" --port "${POSTGRES_PORT:-5432}" --username "${POSTGRES_USER}" \
    --dbname "${POSTGRES_DB}" --format=custom --compress=9 --no-owner --file "${FILE}.partial"
mv "${FILE}.partial" "${FILE}"

# Verify the archive is readable before we trust it.
pg_restore --list "${FILE}" > /dev/null

if [ -n "${BACKUP_ENCRYPTION_KEY:-}" ]; then
    openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -pass env:BACKUP_ENCRYPTION_KEY \
        -in "${FILE}" -out "${FILE}.enc"
    rm -f "${FILE}"
    FILE="${FILE}.enc"
fi
( cd "${BACKUP_DIR}" && sha256sum "$(basename "${FILE}")" > "$(basename "${FILE}").sha256" )

# Off-site copies (optional)
NAME="$(basename "${FILE}")"
if [ -n "${S3_BUCKET:-}" ] && [ -n "${AWS_ACCESS_KEY_ID:-}" ]; then
    REGION="${AWS_REGION:-me-central-1}"
    curl --fail --silent --show-error --aws-sigv4 "aws:amz:${REGION}:s3" \
        --user "${AWS_ACCESS_KEY_ID}:${AWS_SECRET_ACCESS_KEY}" --upload-file "${FILE}" \
        "https://${S3_BUCKET}.s3.${REGION}.amazonaws.com/${S3_PREFIX:-sme-erp/}${NAME}"
    OFFSITE="s3://${S3_BUCKET}/${S3_PREFIX:-sme-erp/}${NAME}"
fi
if [ -n "${AZURE_BLOB_SAS_URL:-}" ]; then
    # Container SAS URL: https://<account>.blob.core.windows.net/<container>?<sas-token>
    BASE="${AZURE_BLOB_SAS_URL%%\?*}"
    SAS="${AZURE_BLOB_SAS_URL#*\?}"
    curl --fail --silent --show-error -X PUT -H "x-ms-blob-type: BlockBlob" --upload-file "${FILE}" \
        "${BASE}/${NAME}?${SAS}"
    OFFSITE="${OFFSITE/none/}${OFFSITE:+ }azure:${BASE##*/}/${NAME}"
fi

# Retention
find "${BACKUP_DIR}" -maxdepth 1 -name 'sme_erp_*' -type f -mtime "+${RETENTION_DAYS}" -print -delete

write_status "success" "Backup completed"
echo "[$(date -Iseconds)] Backup OK: ${FILE} ($(du -h "${FILE}" | cut -f1)), off-site: ${OFFSITE}"
