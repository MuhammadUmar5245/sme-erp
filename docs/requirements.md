# SME-ERP — Requirements and Traceability Matrix

Report reference: §3.5 (Requirements Elicitation) and §3.6 (Requirements Documents: functional and
non-functional requirements). Each requirement is traced to the report section that motivates it, the module
that implements it, the automated tests that verify it and the UAT case(s) in
[testing/uat_test_cases.md](testing/uat_test_cases.md). Functional and behavioural models are in
[diagrams/](diagrams/).

Status of every requirement below: **Implemented and tested** (254 automated tests passing, see
[testing/test_summary.md](testing/test_summary.md)).

## 1. Functional requirements

| ID | Requirement | Report § | Module | Automated tests | UAT |
|---|---|---|---|---|---|
| FR-01 | Users log in with e-mail and password and log out explicitly | 4.6 | accounts | `accounts/tests/test_security.py` | UAT-02 |
| FR-02 | Seven roles (Admin, Manager, Accountant, SalesOfficer, Storekeeper, HROfficer, Viewer) restrict menus, pages and API endpoints (RBAC) | 4.6, 5.1.1 | accounts (`roles.py`) | `accounts/tests/test_permissions.py`, `test_role_access_to_pages`, `test_api_rbac` | UAT-02–04 |
| FR-03 | TOTP two-factor authentication with QR enrolment; mandatory for Admin and Accountant, optional for others | 2.3.6 | accounts | `test_enrolment_*`, `test_user_with_device_must_verify_after_password`, `test_token_endpoint_*` | UAT-05, 06 |
| FR-04 | Immutable audit log of every create/update/delete on business data and every login (user, action, model, object, changes, IP, time), viewable by Admin | 4.6, 2.3.6 | accounts (`audit.py`) | `accounts/tests/test_audit.py` | UAT-10 |
| FR-05 | Admin user management: create, edit, assign roles, deactivate, reset 2FA, unlock | 5.1.1 | accounts | `accounts/tests/test_user_management.py` | UAT-08, 11 |
| FR-06 | Products (SKU, unit, cost, price, VAT rate, reorder level), categories and warehouses (Muscat, Sohar) | 1.3.1, 3.6 | inventory | `test_every_module_page_renders_for_admin`, inventory API tests | UAT-12 |
| FR-07 | Stock computed from IN / OUT / TRANSFER / ADJUST movements that reference their source document; weighted average cost | 1.3.1 | inventory | `inventory/tests/test_services.py` | UAT-13, 14 |
| FR-08 | Low-stock alert list on the dashboard (stock ≤ reorder level) | 3.5.1, 4.5.2 | inventory, core | `test_low_stock_list`, `test_dashboard_lists_low_stock` | UAT-15 |
| FR-09 | Suppliers and purchase orders with Draft → Approved → Received → Billed workflow; approval restricted by role | 1.3.1 | purchasing | `purchasing/tests/test_procure_to_pay.py`, `test_procure_to_pay_over_api` | UAT-16 |
| FR-10 | Goods receipts (partial allowed) create stock IN and post Dr Inventory / Cr GRNI | 1.3.1 | purchasing | `test_full_procure_to_pay`, `test_receipt_is_atomic` | UAT-17 |
| FR-11 | Supplier bills (Dr GRNI, Dr VAT input / Cr AP) and supplier payments (partial allowed) | 1.3.1 | purchasing, finance | `test_full_procure_to_pay`, `test_bill_rules` | UAT-18 |
| FR-12 | Sales orders (Draft → Confirmed → Invoiced) | 1.3.1, 3.6 | sales | `sales/tests/test_order_to_cash.py` | UAT-19 |
| FR-13 | Tax invoices with 5 % Oman VAT per line; posting creates stock OUT and a balanced journal entry in one transaction; blocked when stock is insufficient | 3.6, 4.4.2 | sales | `test_full_order_to_cash`, `test_invoice_blocked_when_stock_insufficient`, `test_invoice_posting_is_atomic` | UAT-19, 20, 23 |
| FR-14 | Customer payments (partial allowed) and credit notes (return to stock, VAT reversal) | 3.6 | sales | `test_full_order_to_cash`, `test_credit_note_returns_stock_and_reverses_revenue` | UAT-21, 22 |
| FR-15 | CRM: customers, contacts, interaction log (call/visit/e-mail/complaint), feedback with CSAT 1–5 | 1.3.1, 1.3.2 | crm | `crm/tests/test_services.py` | UAT-25, 26 |
| FR-16 | Customer 360 page: orders, invoices, outstanding balance, overdue, interactions, average CSAT | 1.3.1, 3.5.2 | crm | `test_customer_360_aggregates`, `test_customer_360_shows_balance_and_csat` | UAT-24 |
| FR-17 | Seeded chart of accounts; journal entries must balance; automatic postings from invoices, payments, credit notes, receipts, bills and supplier payments | 2.2, 3.6 | finance | `finance/tests/test_services.py` | UAT-27 |
| FR-18 | Expenses with input VAT; VAT return summary (output − input, 5 %) | 3.5.1 | finance | `test_expense_posts_vat_input_and_bank`, `test_vat_return_nets_output_and_input` | UAT-28, 29 |
| FR-19 | AR aging, AP aging, trial balance and profit & loss (UI and API) | 3.5.1 | finance | `test_trial_balance_balances_and_pnl`, `test_financial_report_endpoints` | UAT-30 |
| FR-20 | HR: departments, employees, leave requests with approval (Fri–Sat weekend excluded, balance checks, no self-approval) | 1.3.1 | hr | `hr/tests/test_services.py`, `test_leave_approval_ui` | UAT-31, 32 |
| FR-21 | PostgreSQL schema `reporting` with star-schema views: dim_date (2024–2027 with Omani calendar flags), dim_product, dim_customer, dim_supplier, dim_employee, dim_warehouse, fact_sales, fact_purchases, fact_inventory_daily, fact_payments, fact_expenses, fact_feedback, fact_interactions, fact_receivables | 4.4.1, 4.5.2 | reports | `reports/tests/test_reporting.py` | UAT-37 |
| FR-22 | Read-only PostgreSQL role `powerbi_reader` with SELECT on schema `reporting` only | 4.6, 5.1.1 | reports | `test_powerbi_reader_is_read_only_on_reporting_schema` | UAT-37 |
| FR-23 | RESTful reporting API for Power BI's Web connector (`/api/v1/reports/…`): token auth, date filters, pagination | 4.4.1, 4.5.2 | reports | `test_reporting_api_requires_permission_and_supports_token`, `test_every_reporting_endpoint_responds` | UAT-36 |
| FR-24 | In-app dashboard: KPIs (revenue MTD/YTD, gross margin %, receivables, low-stock count, average CSAT) and charts (monthly sales, top 10 products, sales by city, cash in vs out) | 3.5.1, 4.5.1 | reports | `test_kpis`, `test_dashboard_charts`, `test_dashboard_and_builder_pages` | UAT-34 |
| FR-25 | Custom report builder (dataset, date range, group-by, filters, preview) with CSV, Excel and PDF export | 3.5.1 | reports | `test_report_builder_groups_and_filters`, `test_exports` | UAT-35 |
| FR-26 | Import wizard for customers, suppliers, products, opening stock and opening balances (CSV/Excel): upload → column mapping → validation/cleansing preview → dry run → commit | 5.1.3 | integrations | `integrations/tests/test_import_wizard.py` | UAT-38–40 |
| FR-27 | Cleansing rules (trim/case, +968 phones, exact and fuzzy duplicates, missing fields, negative quantities, date formats) and a downloadable cleansing report | 5.1.3 | integrations (`cleansing.py`) | `integrations/tests/test_cleansing.py`, `test_cleansing_report_and_mapping_rules` | UAT-38, 39 |
| FR-28 | CSV/Excel export endpoints for all master data | 3.5.2 | integrations | `test_exports_csv_and_excel`, `test_export_permissions` | UAT-42 |
| FR-29 | POS integration `POST /api/v1/integrations/pos/sales/` with API-key auth and mandatory Idempotency-Key | 3.5.2 | integrations | `integrations/tests/test_pos_and_exports.py` | UAT-41 |
| FR-30 | Monitoring page (Admin): availability, average and p95 response time, error rate, active users, DB size, last backup; same data at `/api/v1/reports/system-metrics/` and `reporting.fact_system_metrics_hourly` | 5.2.3 | monitoring | `monitoring/tests/test_monitoring.py` | UAT-45 |
| FR-31 | Feasibility calculator: ROI, NPV, IRR, payback, discounted payback, 5-year TCO with Al Wadi defaults, cash-flow chart, PDF export, saved scenarios | 2.2.1–2.2.5 | feasibility | `feasibility/tests/test_formulas.py` | UAT-46 |
| FR-32 | Power BI kit: connection guide, Power Query connector, DAX measures, model, 6-page dashboard specification, theme | 4.5, 5.1.1, 5.1.5 | docs/powerbi | column references validated against the views | UAT-36, 37 |
| FR-33 | Realistic demo dataset (`make seed`): 18 months, 120 products, 40 suppliers, 300 customers in 6 cities, ~8,000 invoices with Ramadan/Eid, summer and Khareef seasonality | 3.1, 5.1.4 | core (`seed_demo`) | `core/tests/test_seed_demo.py` | all |
| FR-34 | In-app user evaluation: users rate the ERP and Power BI and report problems; Admin sees the results | 5.1.4, 5.2.3 | core | `core/tests/test_support.py` | UAT-49 |
| FR-35 | Help and support page with support channels, user manual and training material links | 5.1.5, 5.2.1 | core | `core/tests/test_support.py` | UAT-49 |

## 2. Non-functional requirements

| ID | Requirement | Report § | Implementation | Verification | UAT |
|---|---|---|---|---|---|
| NFR-01 | Web UI usable on desktop, tablet and mobile | 2.3.5, 2.3.8, 4.4.1 | Bootstrap 5 responsive layout, off-canvas sidebar below 992 px | manual check | UAT-47 |
| NFR-02 | Encryption in transit: HTTPS only (HTTP→HTTPS redirect, HSTS, TLS 1.2/1.3), TLS to PostgreSQL for Power BI | 4.4.4, 4.6 | nginx, PostgreSQL `ssl=on` | live checks (test_summary §5) | UAT-01 |
| NFR-03 | Encryption at rest: sensitive personal data (civil ID, IBAN) encrypted in the database; optional AES-256 encrypted backups; encrypted cloud disks | 4.6 | `core/fields.py` (Fernet), `backup.sh`, deployment guides | `test_sensitive_fields_are_encrypted_at_rest` | UAT-33 |
| NFR-04 | Account lockout after 5 failed logins (30 min) | 2.3.6 | django-axes | `test_account_locked_after_five_failed_logins` | UAT-07 |
| NFR-05 | Passwords ≥ 12 characters; 30-minute idle session timeout | 2.3.6 | password validators, session settings | `test_password_policy_requires_12_characters`, `test_session_idle_timeout_is_30_minutes` | UAT-09, 11 |
| NFR-06 | RESTful service layer with OpenAPI documentation at `/api/docs/` | 4.4.1 | Django REST Framework, drf-spectacular | `core/tests/test_module_api.py`, `test_openapi_schema_generates` | UAT-36 |
| NFR-07 | Relational database (PostgreSQL 16) with foreign keys, constraints and indexes; money as exact 3-decimal OMR | 4.4.1, 4.4.2 | models and migrations | finance and sales tests | – |
| NFR-08 | Cross-module postings are atomic | 2.3.4 | `transaction.atomic()` in services | `test_invoice_posting_is_atomic`, `test_receipt_is_atomic` | UAT-20 |
| NFR-09 | Modular design: one Django app per module, modules can be enabled independently in the menu | 4.1 | 11 apps, permission-driven navigation | page/RBAC tests | – |
| NFR-10 | Daily compressed, checksummed backups with 14-day retention and optional S3/Azure off-site copy | 5.2.2 | `scripts/backup.sh`, cron service | restore test (disaster_recovery.md §6) | UAT-43 |
| NFR-11 | RPO 24 h and RTO 4 h with a tested restore procedure | 5.2.2 | `scripts/restore.sh`, `make restore` | measured restore 3 s, recovery ≈ 15 s | UAT-44 |
| NFR-12 | Performance monitoring of every request (count, response time, errors per endpoint), visible in-app and in Power BI | 5.2.3, 2.3.2 | monitoring middleware | `test_middleware_records_requests_per_endpoint` | UAT-45 |
| NFR-13 | Performance: 50 concurrent users with no errors and median response < 200 ms | 2.3.2, 3.5.5 | gunicorn + nginx + PostgreSQL | Locust: 0 failures, median 73 ms | UAT-48 |
| NFR-14 | Availability 24/7: health checks, automatic container restart, availability measurement | 3.5.4, 2.3.4 | `/health/`, Docker `restart: unless-stopped`, health probes | `test_health_reports_database_ok`, `test_availability_counts_missing_probes_as_downtime` | UAT-45 |
| NFR-15 | Scalability: stateless web tier behind a reverse proxy, managed PostgreSQL, horizontal scaling in the cloud | 3.5.5, 2.3.3 | Docker images, deployment guides | deployment_azure.md / deployment_aws.md | – |
| NFR-16 | Maintainability: automated tests with ≥ 80 % coverage on business logic, documented code and APIs | 2.3.7 | pytest + coverage gate in `make test` | 93.3 % on services | – |
| NFR-17 | Usability: consistent layout, search, filters and pagination on every list, inline validation messages | 3.5.3, 2.3.9 | generic list/form templates with HTMX live search | page tests | UAT-12–35 |
| NFR-18 | Secrets only in `.env` (never committed); `.env.example` documents every setting | 4.6 | django-environ, `.gitignore` | repository review | – |
