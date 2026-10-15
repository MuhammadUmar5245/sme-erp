# Backup / cron service: PostgreSQL 16 client tools + cron + curl (S3 SigV4 / Azure Blob uploads).
FROM postgres:16

RUN apt-get update \
    && apt-get install -y --no-install-recommends cron curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY docker/backup/entrypoint.sh /usr/local/bin/backup-entrypoint.sh
RUN chmod +x /usr/local/bin/backup-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/backup-entrypoint.sh"]
