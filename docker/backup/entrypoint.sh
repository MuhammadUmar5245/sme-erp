#!/bin/bash
# Cron container: schedule the daily database backup (default 02:00 Asia/Muscat).
set -e

# cron does not pass the container environment to jobs, so persist the variables backup.sh needs.
env | grep -E '^(POSTGRES_|BACKUP_|AWS_|S3_|AZURE_|TZ=)' | sed 's/^/export /; s/=\(.*\)$/="\1"/' > /etc/backup.env
chmod 600 /etc/backup.env

SCHEDULE="${BACKUP_SCHEDULE:-0 2 * * *}"
cat > /etc/cron.d/sme-erp-backup <<CRON
SHELL=/bin/bash
${SCHEDULE} root . /etc/backup.env && /scripts/backup.sh >> /var/log/backup.log 2>&1
CRON
chmod 644 /etc/cron.d/sme-erp-backup
touch /var/log/backup.log

echo "Backup schedule: '${SCHEDULE}' (${TZ:-UTC}); retention ${BACKUP_RETENTION_DAYS:-14} days"
if [ "${BACKUP_ON_START:-0}" = "1" ]; then
    /scripts/backup.sh >> /var/log/backup.log 2>&1 || true
fi
cron
exec tail -F /var/log/backup.log
