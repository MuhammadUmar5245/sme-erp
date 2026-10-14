# SME-ERP — Project Context

## What this is
Academic Business Information Systems project: a cloud-based, modular ERP for SMEs
with Power BI integration for real-time analytics. The written report (Chapters 1–6)
already exists (see docs/report/project_report.txt); read it before major design decisions. The code MUST match what the report describes:
modular cloud ERP, RESTful service layer, RDBMS (PostgreSQL), web UI usable on desktop,
tablet and mobile, RBAC, encryption in transit and at rest, Power BI dashboards, data
migration and cleansing, backup/DR, performance monitoring, and unit/integration/UAT testing.

## Case company (fictional, used for seed data and screenshots)
Al Wadi Trading & Distribution LLC — Muscat, Sultanate of Oman. Wholesale and distribution SME
(FMCG and household goods), ~45 employees, head office in Muscat plus warehouses in Muscat and Sohar.
Currency OMR (3 decimal places / baisa). Timezone Asia/Muscat. VAT 5% (Oman). Weekend Friday–Saturday.
Language of UI: English (Arabic labels optional later).

## Tech stack (do not change without asking)
- Python 3.12, Django 5.x, Django REST Framework
- PostgreSQL 16
- Bootstrap 5 server-rendered templates + HTMX for interactivity, Chart.js for in-app charts
- Docker Compose services: web (gunicorn), db (postgres), nginx (TLS reverse proxy)
- pytest + pytest-django + factory_boy, coverage
- django-otp (TOTP 2FA), django-axes (login lockout), django-filter, drf-spectacular (OpenAPI)

## Modules (one Django app each)
accounts (users, roles, 2FA, audit log) · inventory · purchasing · sales · crm ·
finance · hr · reports · integrations (import/export, data migration) · monitoring ·
feasibility (ROI/NPV/IRR/TCO calculator)

## Roles (Django groups)
Admin, Manager, Accountant, SalesOfficer, Storekeeper, HROfficer, Viewer.
A separate read-only PostgreSQL role `powerbi_reader` is used ONLY for Power BI.

## Conventions
- Business logic lives in `services.py` per app; views and serializers stay thin.
- Cross-module postings (invoice -> stock movement + journal entry) run inside
  `transaction.atomic()`.
- All money fields: DecimalField(max_digits=14, decimal_places=3) (OMR uses 3 decimals). Never float.
- API base path: /api/v1/ ; OpenAPI docs at /api/docs/
- Reporting SQL views live in PostgreSQL schema `reporting`, named fact_* and dim_*.
- Secrets only in `.env` (provide `.env.example`). Never commit secrets.
- Every service function has tests. Run `make test` before saying a task is done.
- Docs go in /docs, diagrams as Mermaid (.md) so they render on GitHub.

## Commands
make up | make down | make migrate | make seed | make test | make backup | make restore

## Definition of done (every feature)
model + migration · admin registration · permission-checked API endpoint ·
responsive UI page · tests passing · docs/requirements.md traceability updated

## Build prompts
Phase-by-phase instructions are in /prompts (00 to 10). Do only the phase the user asks for.
