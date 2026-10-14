# SME-ERP + Power BI — Claude Code Build Script

## How to use

1. Create an empty folder, e.g. `sme-erp`, and run `git init` inside it.
2. Save **Part A** below as `CLAUDE.md` in the root of that folder. Claude Code reads this file automatically in every session.
3. Run `claude` inside the folder.
4. Paste the **Part B** phase prompts **one at a time**. Review and test each phase, then commit before moving to the next.
5. Run Phase 0 in plan mode so you approve the design before any code is written.

Requirements: Docker Desktop, Git, Python 3.12 (optional, for running outside Docker). You need Windows with **Power BI Desktop** for Phase 9. Claude Code cannot author `.pbix` files, so it generates the data model, DAX and M scripts, and you build the report in Power BI Desktop.

---

## PART A — `CLAUDE.md`

```markdown
# SME-ERP — Project Context

## What this is
Academic Business Information Systems project: a cloud-based, modular ERP for SMEs
with Power BI integration for real-time analytics. The written report (Chapters 1–6)
already exists; the code MUST match what the report describes:
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
```

---

## PART B — Phase prompts (paste one at a time)

### Phase 0 — Plan (plan mode)

```
Read CLAUDE.md. Do NOT write code yet. Produce a plan containing:
1. Final folder structure.
2. ERD for all modules (Mermaid erDiagram) with key fields and relationships.
3. List of REST endpoints per module with the roles allowed.
4. The order-to-cash and procure-to-pay flows, showing which tables each step writes to.
5. Any risks or ambiguities you see.
Save the plan to docs/plan.md and wait for my approval.
```

### Phase 1 — Scaffold

```
Implement the project skeleton per docs/plan.md:
- docker-compose.yml with web, db and nginx. nginx serves HTTPS with a self-signed cert
  (script in scripts/gen_cert.sh) and redirects HTTP to HTTPS.
- Django project `config` with split settings (base/dev/prod) reading from .env; .env.example.
- Makefile with the commands listed in CLAUDE.md.
- Base responsive layout: sidebar navigation per module (collapses on mobile), top bar
  with user menu, login/logout pages, and a placeholder dashboard.
- Health check endpoint /health/ returning DB status.
- pytest configured; one smoke test.
Verify that `make up` and `make test` pass, then commit.
```

### Phase 2 — Accounts and security

```
Build the accounts app:
- Custom User model (email login), Department FK, phone.
- Create the 7 role groups with model-level permissions via a data migration.
  Restrict UI menus and API endpoints by role.
- TOTP 2FA with django-otp: mandatory for Admin and Accountant, optional for others.
  Include a QR enrolment page.
- django-axes lockout after 5 failed logins; 12+ character password policy;
  30-minute idle session timeout.
- AuditLog model (user, action, model, object_id, changes JSON, IP, timestamp) written
  automatically on create/update/delete of business models through signals or a mixin.
  Read-only audit viewer page for Admin.
- Admin user-management UI.
Tests for permissions, lockout and audit logging. Commit.
```

### Phase 3 — Core business modules

```
Build these modules with models, services, API, UI (list/detail/create/edit with
search, filter and pagination) and tests:

INVENTORY: Category, Product (SKU, unit, cost price, sale price, reorder level),
Warehouse, StockMovement (IN/OUT/TRANSFER/ADJUST, with reference to the source document).
Current stock is computed from movements. Low-stock alert list on the dashboard.

PURCHASING: Supplier, PurchaseOrder + lines (Draft -> Approved -> Received -> Billed),
GoodsReceipt that creates stock IN movements, SupplierBill.

SALES: SalesOrder + lines, Invoice with 5% Oman VAT per line (creates stock OUT and a journal entry),
Payment (partial payments allowed), Credit note. Block an invoice if stock is insufficient.

CRM: Customer (link to sales), Contact, Interaction log (call/visit/email/complaint),
Feedback with a satisfaction score of 1–5. Customer 360 page showing orders,
outstanding balance, interactions and average CSAT.

FINANCE: simple chart of accounts (seeded), JournalEntry + lines (must balance),
automatic postings from invoices, payments and supplier bills, Expense entry,
VAT output/input accounts and a VAT return summary (5%), AR aging and AP aging reports,
trial balance, simple P&L.

HR (lite): Employee, Department, Leave requests with an approval workflow.

All cross-module postings must be atomic. Write integration tests for the full
order-to-cash and procure-to-pay flows. Commit after each module.
```

### Phase 4 — Reporting layer and Power BI service API

```
1. Create a PostgreSQL schema `reporting` via migrations with star-schema views:
   dim_date (2024–2027), dim_product, dim_customer, dim_supplier, dim_employee,
   dim_warehouse, fact_sales (line level), fact_purchases, fact_inventory_daily
   (stock per product per warehouse per day), fact_payments, fact_expenses, fact_feedback.
2. A migration/script that creates the read-only role `powerbi_reader` with SELECT only
   on schema `reporting`. The password comes from .env.
3. DRF read-only reporting endpoints under /api/v1/reports/ (token auth, date-range
   filters, pagination) that mirror the fact/dim views, for Power BI's Web connector.
4. In-app dashboard (Chart.js) with KPI cards: revenue MTD/YTD, gross margin %,
   outstanding receivables, low-stock count, average CSAT; charts for monthly sales trend,
   top 10 products, sales by city, and cash in vs. out.
5. Custom report builder page: choose dataset, date range, group-by and filters;
   preview the table; export to CSV, Excel and PDF.
Tests for the views and endpoints. Commit.
```

### Phase 5 — Data migration and integrations

```
Build the integrations app:
- Import wizard for Customers, Suppliers, Products, Opening Stock and Opening Balances
  from CSV/Excel. Steps: upload -> column mapping UI -> validation and cleansing preview ->
  dry run -> commit.
- Cleansing rules: trim and normalise case, phone format (+968), duplicate detection
  (exact plus fuzzy name match), invalid or missing required fields, negative quantities,
  date format normalisation. Produce a downloadable cleansing report (rows fixed,
  rejected, and why).
- Put sample "legacy system" files with deliberately dirty data in sample_data/legacy/
  for the demo.
- Export endpoints (CSV/Excel) for all master data.
- POS integration endpoint: POST /api/v1/integrations/pos/sales/ (API-key auth) that
  creates invoices; idempotency key required.
Tests included. Commit.
```

### Phase 6 — Realistic seed data

```
Create a management command `seed_demo` (deterministic, random seed 42) for Al Wadi Trading
Distributors: 18 months of data ending today; ~120 products in 8 categories;
40 suppliers; 300 customers across Muscat, Seeb, Sohar, Salalah, Nizwa, Sur;
~8,000 invoices with seasonality (Ramadan/Eid spikes, slow summer months June–August, Khareef season boost in Salalah);
realistic payment delays for AR aging; feedback records; employees and leave records;
a few stock-outs. `make seed` must reset and reload. Print summary counts at the end.
```

### Phase 7 — Operations: backup, DR, monitoring and feasibility

```
1. scripts/backup.sh: pg_dump compressed, timestamped, 14-day retention, optional
   upload to S3/Azure Blob if env vars are set. scripts/restore.sh with confirmation.
   A cron service in docker-compose runs a daily backup. Document RPO = 24h and
   RTO = 4h in docs/disaster_recovery.md, with a tested restore procedure.
2. Monitoring app: middleware recording request count, response time and errors per
   endpoint. Monitoring page (Admin only) showing uptime, average/p95 response time,
   error rate, active users, DB size, last backup time and status. Expose the same data
   at /api/v1/reports/system-metrics/ for Power BI.
3. Feasibility app: calculator page for ROI, NPV, IRR, payback period and 5-year TCO.
   Input fields cover licence/subscription, implementation, training, maintenance,
   expected savings and discount rate. Prefill defaults for Al Wadi Trading (OMR), show a
   cash-flow chart, and export the results to PDF.
Tests for the financial formulas against known values. Commit.
```

### Phase 8 — Testing and UAT

```
- Raise test coverage to >= 80% on services; add a coverage report to `make test`.
- Write docs/testing/uat_test_cases.md: at least 40 UAT cases (ID, module, role,
  preconditions, steps, expected result, actual result, status) covering every module,
  security (RBAC, 2FA, lockout), import/cleansing, reports and backup/restore.
- Write docs/testing/test_summary.md with the unit/integration results table.
- Optional: a locustfile.py load test for 50 concurrent users, with results recorded.
```

### Phase 9 — Power BI kit

```
Create docs/powerbi/ containing:
1. connection_guide.md: connecting Power BI Desktop to PostgreSQL (Npgsql) using
   powerbi_reader on schema `reporting`; Import vs DirectQuery (use DirectQuery for
   near-real-time stock and sales); alternative Web/API connector using a token;
   on-premises data gateway and scheduled refresh in the Power BI Service.
2. powerquery_api.m: M code for the paginated API connector.
3. measures.dax: Total Revenue, Revenue MTD/YTD, YoY Growth %, Gross Margin %,
   Avg Order Value, Inventory Value, Inventory Turnover, Days Inventory Outstanding,
   Stock-out Count, DSO, Overdue Receivables, Cash In, Cash Out, Net Cash Flow, Avg CSAT,
   Complaint Rate, 3-month Moving-Average Sales Forecast.
4. model.md: relationships (star schema), date table marking, hierarchies.
5. dashboard_spec.md: page-by-page layout for 5 pages (Executive Overview, Sales,
   Inventory, Finance, Customer/CRM) plus a System Health page — visual type, fields,
   slicers and conditional formatting for each.
6. A theme JSON file matching the ERP colours.
```

### Phase 10 — Documentation for the report

```
Generate the following in /docs:
- requirements.md: Functional (FR-01...) and Non-functional (NFR-01...) requirements
  tables, each traced to the report section (e.g. 3.5.1, 2.3.6) and to the
  implementing module and test case.
- diagrams/ (Mermaid): use case diagram, DFD Level 0 and Level 1, ERD, activity diagram
  (order-to-cash), sequence diagram (invoice posting), deployment/architecture diagram
  (users -> HTTPS -> nginx -> Django -> PostgreSQL -> reporting schema -> Power BI).
- user_manual.md per role, with screenshot placeholders named for each page.
- training_plan.md (sessions, audience, duration, materials).
- deployment_azure.md (nearest Middle East region; App Service + Azure Database for PostgreSQL + Blob backup) and
  deployment_aws.md (Middle East region; EC2/ECS + RDS + S3).
- project_signoff.md template (sponsor, deliverables checklist, signatures, date).
- README.md: setup, demo logins per role, screenshots section.
```
