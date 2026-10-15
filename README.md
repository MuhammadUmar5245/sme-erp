# SME-ERP with Power BI – Al Wadi Trading & Distribution LLC

A cloud-ready, modular ERP for small and medium-sized enterprises with Power BI integration for real-time
analytics. It is the implementation of the Business Information Systems project report
([docs/report/project_report.txt](docs/report/project_report.txt), Chapters 1–6). The case company is
**Al Wadi Trading & Distribution LLC** (Muscat, Oman; FMCG and household-goods distribution, ~45 staff,
warehouses in Muscat and Sohar, OMR with 3 decimals, VAT 5 %, Friday–Saturday weekend).

| Report requirement | Where it is implemented |
|---|---|
| Modular cloud ERP (§4.1, §4.4.1) | 11 Django apps: accounts, inventory, purchasing, sales, crm, finance, hr, reports, integrations, monitoring, feasibility |
| RESTful service layer (§4.4.1) | `/api/v1/` (Django REST Framework), OpenAPI docs at `/api/docs/` |
| RDBMS (§4.4.2) | PostgreSQL 16 with foreign keys, constraints and indexes |
| Web UI for desktop, tablet and mobile (§2.3.5, §2.3.8) | Bootstrap 5 + HTMX, collapsible sidebar |
| RBAC, 2FA, encryption in transit and at rest (§2.3.6, §4.6) | 7 roles, TOTP 2FA, lockout, audit log, HTTPS/TLS, PostgreSQL SSL, encrypted personal data and backups |
| Power BI dashboards (§4.5) | `reporting` star schema, read-only `powerbi_reader`, reporting API, Power BI kit in [docs/powerbi/](docs/powerbi/) |
| Data migration and cleansing (§5.1.3) | Import wizard with cleansing rules and reports, dirty sample files in `sample_data/legacy/` |
| Backup and DR (§5.2.2) | Daily backups (cron), restore script, RPO 24 h / RTO 4 h, tested restore |
| Performance monitoring (§5.2.3) | Request metrics, availability, monitoring page and system-metrics API |
| Feasibility (§2.2) | ROI / NPV / IRR / payback / TCO calculator with PDF export |
| Testing (§5.1.2) | 254 automated unit/integration tests (93 % coverage on business logic), 49 UAT cases, 50-user load test |

## Quick start

### Prerequisites
- **Docker Desktop** (Windows/macOS) or Docker Engine + Compose v2 (Linux) – must be running.
- **Git**. Python and `make` are *not* required on your computer: everything runs in containers.
  On Windows use `.\make.ps1 <command>` in PowerShell instead of `make <command>`.
- Free ports 80, 443 and 5432 (change `HTTP_PORT`, `HTTPS_PORT`, `DB_HOST_PORT` in `.env` if they are taken).

### Setup
```bash
git clone <repository-url> sme-erp && cd sme-erp
cp .env.example .env         # Windows: copy .env.example .env  (make up also does this)
# Edit .env: set DJANGO_SECRET_KEY, FIELD_ENCRYPTION_KEY, POSTGRES_PASSWORD, POWERBI_READER_PASSWORD
make up                      # Windows: .\make.ps1 up   (builds images, creates TLS certificate, migrates)
make seed                    # Windows: .\make.ps1 seed (≈ 6 minutes: 18 months of demo data)
```
Generate a field-encryption key with
`docker compose run --rm web python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.

### Open the application
1. Browse to **https://localhost** (http:// is redirected to https://).
2. The local certificate is self-signed (`certs/server.crt`, made by `scripts/gen_cert.sh`), so the browser warns
   once: choose *Advanced → Continue to localhost*. To remove the warning, import `certs/server.crt` into your
   trusted root certificates. Production uses a real certificate (see the deployment guides).
3. Log in with one of the demo accounts below.

### Demo logins (created by `make seed`)

Password for every account: **`AlWadi-Demo-2026!`**

| Role | E-mail | Can do | 2FA |
|---|---|---|---|
| Admin | `admin@alwadi.om` | Everything: users, roles, audit log, monitoring, imports, Django admin | **Mandatory** – scan the QR code at first login |
| Manager | `manager@alwadi.om` | Approve POs and leave, dashboards, report builder, feasibility | Optional |
| Accountant | `accountant@alwadi.om` | Finance, bills, payments, VAT, aging, imports | **Mandatory** |
| SalesOfficer | `sales@alwadi.om` | Customers, CRM, sales orders, invoices, receipts | Optional |
| Storekeeper | `store@alwadi.om` | Products, stock, transfers, goods receipts | Optional |
| HROfficer | `hr@alwadi.om` | Employees, departments, leave | Optional |
| Viewer | `viewer@alwadi.om` | Read-only business data and dashboards | Optional |

Also created: `powerbi@alwadi.om` (Viewer, API token for Power BI), `rep1–rep4@alwadi.om` (sales reps).
`make seed` prints the Power BI API token and a POS API key at the end – copy them, the POS key is shown once.
For 2FA, install Google Authenticator or Microsoft Authenticator on your phone.

## Commands

| Command | What it does |
|---|---|
| `make up` / `make down` | Start / stop the stack (certs, db, web, nginx, cron) |
| `make migrate` | Apply database migrations (also run automatically when the web container starts) |
| `make seed` | **Reset** the database and load the Al Wadi demo data (deterministic, seed 42) |
| `make test` | Run all tests with a coverage report; fails if business-logic coverage < 80 % |
| `make backup` | Back up the database now (`backups/`) |
| `make restore FILE=latest` | Restore a backup (asks you to type RESTORE) – see [docs/disaster_recovery.md](docs/disaster_recovery.md) |
| `make logs`, `make shell`, `make cert` | Follow logs, Django shell, regenerate the TLS certificate |

Windows: `.\make.ps1 up`, `.\make.ps1 test`, `.\make.ps1 restore latest`, …

## Useful URLs

| URL | Purpose |
|---|---|
| https://localhost/ | ERP home dashboard (KPIs, low-stock alerts) |
| https://localhost/reports/dashboard/ | Analytics dashboard (Chart.js) |
| https://localhost/reports/builder/ | Report builder with CSV / Excel / PDF export |
| https://localhost/integrations/imports/ | Data-migration wizard |
| https://localhost/monitoring/ | System monitoring (Admin) |
| https://localhost/feasibility/ | ROI / NPV / IRR / TCO calculator |
| https://localhost/api/docs/ | REST API documentation (Swagger) |
| https://localhost/api/v1/reports/ | Power BI datasets (token) |
| https://localhost/health/ | Health check (application + database) |
| https://localhost/admin/ | Django admin (Admin role) |

## Power BI

- **PostgreSQL connector** (recommended, DirectQuery for live stock and sales): server `localhost:5432`,
  database `sme_erp`, user `powerbi_reader`, password `POWERBI_READER_PASSWORD` from `.env`, schema `reporting`.
- **Web/API connector**: [docs/powerbi/powerquery_api.m](docs/powerbi/powerquery_api.m) with the token printed by `make seed`.
- Model, DAX measures, six dashboard pages and the theme: [docs/powerbi/](docs/powerbi/).

## Documentation

| Document | Content |
|---|---|
| [docs/plan.md](docs/plan.md) | Implementation plan, folder structure, endpoint list, business flows |
| [docs/requirements.md](docs/requirements.md) | Functional / non-functional requirements traced to report sections, modules, tests and UAT |
| [docs/diagrams/](docs/diagrams/) | Use case, DFD level 0/1, ERD, order-to-cash activity, invoice-posting sequence, deployment architecture (Mermaid) |
| [docs/user_manual.md](docs/user_manual.md) | User manual per role (with screenshot placeholders) |
| [docs/training_plan.md](docs/training_plan.md) | Training sessions, audiences, durations, materials, evaluation |
| [docs/testing/](docs/testing/) | UAT test cases and test summary (unit/integration, coverage, load test) |
| [docs/disaster_recovery.md](docs/disaster_recovery.md) | Backup and DR plan, RPO/RTO, tested restore procedure |
| [docs/deployment_azure.md](docs/deployment_azure.md) / [docs/deployment_aws.md](docs/deployment_aws.md) | Cloud deployment (UAE North / me-central-1) |
| [docs/powerbi/](docs/powerbi/) | Power BI connection guide, Power Query, DAX, model, dashboard spec, theme |
| [docs/project_signoff.md](docs/project_signoff.md) | Project sign-off template |

## Screenshots

Capture these from the seeded demo and save them in `docs/screenshots/` (names match the user manual):

| Screen | File |
|---|---|
| Login | `docs/screenshots/01-login.png` |
| 2FA enrolment (QR) | `docs/screenshots/02-2fa-setup.png` |
| Home dashboard / mobile | `docs/screenshots/03-dashboard.png`, `03-dashboard-mobile.png` |
| Analytics dashboard | `docs/screenshots/20-manager-analytics.png` |
| Report builder | `docs/screenshots/21-manager-report-builder.png` |
| Feasibility calculator | `docs/screenshots/22-manager-feasibility.png` |
| Invoice with VAT | `docs/screenshots/30-accountant-invoice.png` |
| VAT return / AR aging | `docs/screenshots/31-accountant-vat.png`, `32-accountant-ar-aging.png` |
| Customer 360 | `docs/screenshots/40-sales-customer-360.png` |
| Stock levels | `docs/screenshots/50-store-stock-levels.png` |
| Import wizard preview | `docs/screenshots/71-import-preview.png` |
| System monitoring | `docs/screenshots/12-admin-monitoring.png` |
| Power BI executive overview | `docs/screenshots/80-powerbi-executive.png` |

## Project structure

```text
config/        Django settings (base/dev/prod/test), URLs, API router
core/          shared base models, generic CRUD views, dashboard, help & support, seed_demo command
accounts/ inventory/ purchasing/ sales/ crm/ finance/ hr/      business modules (models, services, API, views, tests)
reports/       reporting schema (dim_*/fact_*), Power BI API, dashboard KPIs, report builder
integrations/  import wizard + cleansing, exports, POS API
monitoring/    request metrics, health probes, system-metrics API
feasibility/   ROI / NPV / IRR / payback / TCO
templates/ static/   Bootstrap 5 UI
docker/ scripts/     Dockerfiles, nginx, cron, TLS certificate, backup and restore
sample_data/legacy/  dirty legacy files for the migration demo
loadtest/            Locust 50-user load test and results
docs/                documentation (see above)
```
Business logic lives in each app's `services.py`; cross-module postings (invoice → stock movement + journal
entry) run inside `transaction.atomic()`. All money is `Decimal(14,3)`.

## Operations and maintenance (report §5.2.1)

**Upgrading to a new version**
1. `make backup` (keep the file name).
2. `git pull` (or deploy the new image tag).
3. `make up` – images are rebuilt and migrations run automatically when the web container starts.
4. `make test` on the staging copy before production; check `https://<host>/health/` and the monitoring page.
5. If something is wrong: `make restore FILE=<backup from step 1>` and redeploy the previous version.

**Routine schedule**: daily backup check (monitoring page), weekly off-site backup check, monthly security
updates of the Docker base images (`docker compose build --pull`), quarterly restore test, yearly review of
roles and users (audit log).

## Troubleshooting

| Problem | Fix |
|---|---|
| `failed to connect to the docker API` | Start Docker Desktop and wait until it says *running* |
| Port 80/443/5432 already in use | Change `HTTP_PORT`, `HTTPS_PORT`, `DB_HOST_PORT` in `.env`, then `make up` |
| Browser certificate warning | Expected with the self-signed local certificate (see *Open the application*) |
| "Account temporarily locked" | Wait 30 minutes, or Admin → Users → *Unlock* |
| Lost 2FA phone | Admin → Users → user → *Reset 2FA*; the user enrols again at next login |
| Git Bash rewrites `/scripts/...` paths in `docker compose exec` | Prefix the command with `MSYS_NO_PATHCONV=1`, or use PowerShell / `make.ps1` |
| `make seed` refuses to run | It needs `--reset` when data exists; `make seed` already passes it |

## Development notes

- Built phase by phase (Agile iterations, report §4.2); see `git log` (Phase 1 … Phase 10) and `prompts/`.
- Tests run inside Docker against PostgreSQL: `make test` (or `docker compose run --rm web pytest`).
- Secrets live only in `.env` (never committed); `.env.example` documents every setting.
