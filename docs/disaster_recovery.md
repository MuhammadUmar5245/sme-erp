# Backup and Disaster Recovery Plan

Report reference: §5.2.2 (Backup and Disaster Recovery), §2.3.4 (Reliability), §3.5.4 (Availability).

## 1. Objectives

| Objective | Target | How it is met |
|---|---|---|
| **RPO** (Recovery Point Objective) – maximum data loss | **24 hours** | Automatic daily backup at 02:00 Asia/Muscat; the monitoring page flags a backup older than 24 h |
| **RTO** (Recovery Time Objective) – maximum downtime | **4 hours** | Scripted restore (seconds) plus documented server rebuild (< 1 hour); tested below |
| Retention | 14 days on the server, longer off-site | `BACKUP_RETENTION_DAYS=14`; S3 / Azure lifecycle rules for off-site copies |

## 2. What is backed up

- The whole PostgreSQL database `sme_erp` (all modules, audit log, reporting views, Power BI grants) via `pg_dump` custom format (compressed).
- Each backup has a **SHA-256 checksum** file and is verified with `pg_restore --list` before it is accepted.
- Optional **AES-256 encryption at rest** (`BACKUP_ENCRYPTION_KEY`), so a stolen backup file is unreadable. Sensitive HR fields are already encrypted inside the database (Fernet).
- Not in the backup (kept in the deployment repository / password manager): source code, `.env` secrets, TLS certificates.

## 3. Components

| Item | Location |
|---|---|
| Backup script | `scripts/backup.sh` (timestamped `sme_erp_YYYYmmdd_HHMMSS.dump`, retention, off-site upload, status file) |
| Restore script | `scripts/restore.sh` (checksum check, typed confirmation `RESTORE`, decryption, single-transaction restore) |
| Scheduler | `cron` service in `docker-compose.yml` (`BACKUP_SCHEDULE`, default `0 2 * * *`, plus one backup on start) |
| Local backups | `./backups/` on the host (bind mount) |
| Off-site (optional) | Amazon S3 in a Middle East region (`S3_BUCKET`, `AWS_*`) and/or Azure Blob (`AZURE_BLOB_SAS_URL`) |
| Status | `backups/last_backup.json` → **System monitoring** page and `GET /api/v1/reports/system-metrics/` (Power BI System Health page) |

## 4. Daily operation

1. The cron container runs `backup.sh` every night at 02:00.
2. The administrator checks **Administration → System monitoring**: "Last backup" must show *Success* and *age < 24 h*. A failed or late backup shows a red/amber badge.
3. Manual backup before risky changes (upgrades, mass imports): `make backup` (Windows: `.\make.ps1 backup`).

## 5. Restore procedure (tested)

Scenario A – data corruption or a bad import on a working server:

```bash
make restore FILE=latest                         # or FILE=sme_erp_20261015_020000.dump
# Windows: .\make.ps1 restore latest
```
`make restore` stops the web application, runs `restore.sh` (which lists the file, checks its checksum and asks you to
type `RESTORE`), restores in a single transaction and starts the application again. Then:

1. Open `https://localhost/health/` → `{"status": "ok", "database": "ok"}`.
2. Log in, open the dashboard and the latest invoices; run **Finance → Financial reports → Trial balance** (must be *Balanced*).
3. Tell users which data after the backup time must be re-entered (RPO window).

Scenario B – server lost (disk failure, ransomware, cloud region outage):

1. Provision a new VM / App Service in the same or the secondary region (see `docs/deployment_azure.md`, `docs/deployment_aws.md`).
2. `git clone` the repository, restore `.env` from the password manager, `make up` (≈ 10 min including image builds).
3. Download the newest backup from S3 / Azure Blob into `./backups/` (and its `.sha256`).
4. `make restore FILE=<file>`; verify as above.
5. Point DNS to the new server; re-run `python manage.py setup_powerbi_reader` if the Power BI password changed; refresh Power BI.

## 6. Restore test record

| Date | Backup file | Size | Test | Result |
|---|---|---|---|---|
| 2026-10-15 10:56 | `sme_erp_20261015_105645.dump` | 3.9 MB (8,009 invoices, 22,625 journal entries) | Inserted a "disaster marker" customer after the backup, stopped web, `restore.sh latest --yes`, started web | **Pass**: restore finished in **3 s**; marker row gone; 8,009 invoices and 22,625 journal entries present; trial balance difference 0.000; all 15 reporting views and the `powerbi_reader` grants restored; application healthy 12 s after start |

Findings fixed during the test: nginx cached the old IP address of the web container after it was restarted and
returned HTTP 502. nginx now resolves `web` through Docker DNS on each request (`docker/nginx/nginx.conf`); a
re-test showed the site back in 12 s with no manual action.

**Measured recovery time (Scenario A): about 15 seconds** of downtime, far inside the 4-hour RTO. Scenario B is
dominated by provisioning and download time and is estimated at under 1 hour.

## 7. Responsibilities and testing schedule

| Task | Owner | Frequency |
|---|---|---|
| Check the backup status on the monitoring page | IT & ERP Administrator | Daily |
| Copy/verify off-site backups | IT & ERP Administrator | Weekly |
| Restore test into a separate environment (Scenario A) | IT & ERP Administrator + Finance Manager | Quarterly |
| Full rebuild drill (Scenario B) | IT provider | Yearly |
| Review RPO/RTO with management | General Manager | Yearly |
