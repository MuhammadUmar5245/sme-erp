# SME-ERP — Requirements and Traceability

Each requirement is traced to the written report section that motivates it, the module that
implements it, and the automated tests / UAT cases that verify it.

## Functional requirements

| ID | Requirement | Report § | Module | Tests |
|---|---|---|---|---|
| FR-01 | Users log in with e-mail and password; log out explicitly | 4.6 | accounts | `accounts/tests/test_security.py` |
| FR-02 | Seven roles (Admin, Manager, Accountant, SalesOfficer, Storekeeper, HROfficer, Viewer) restrict menus, pages and API endpoints | 4.6, 5.1.1 | accounts (`roles.py`) | `accounts/tests/test_permissions.py` |
| FR-03 | TOTP two-factor authentication with QR enrolment; mandatory for Admin and Accountant | 2.3.6 | accounts | `test_security.py::test_enrolment_*`, `test_user_with_device_must_verify_after_password` |
| FR-04 | Every create/update/delete on business data and every login is written to an immutable audit log, viewable by Admin | 4.6, 2.3.6 | accounts (`audit.py`) | `accounts/tests/test_audit.py` |
| FR-05 | Admin manages users: create, edit, assign roles, deactivate, reset 2FA, unlock | 5.1.1 | accounts | `accounts/tests/test_user_management.py` |
| FR-06 | Maintain products (SKU, unit, cost, price, reorder level), categories and warehouses (Muscat, Sohar) | 1.3.1, 3.6 | inventory | `core/tests/test_module_pages.py`, `inventory/tests/test_services.py` |
| FR-07 | Stock is computed from IN/OUT/TRANSFER/ADJUST movements referencing their source document; weighted average cost | 1.3.1 | inventory | `inventory/tests/test_services.py` |
| FR-08 | Low-stock alert list on the dashboard (stock ≤ reorder level) | 3.5.1, 4.5.2 | inventory, core | `test_low_stock_list`, `test_dashboard_lists_low_stock` |
| FR-09 | Suppliers and purchase orders with Draft → Approved → Received → Billed workflow; approval restricted by role | 1.3.1 | purchasing | `purchasing/tests/test_procure_to_pay.py`, `test_procure_to_pay_over_api` |
| FR-10 | Goods receipts (partial allowed) create stock IN movements and post Dr Inventory / Cr GRNI | 1.3.1 | purchasing | `test_full_procure_to_pay`, `test_receipt_is_atomic` |
| FR-11 | Supplier bills (Dr GRNI, Dr VAT input / Cr AP) and supplier payments (partial allowed) | 1.3.1 | purchasing, finance | `test_full_procure_to_pay` |
| FR-12 | Sales orders (Draft → Confirmed → Invoiced) | 1.3.1, 3.6 | sales | `sales/tests/test_order_to_cash.py` |
| FR-13 | Tax invoices with 5% Oman VAT per line create stock OUT and a balanced journal entry atomically; invoices are blocked when stock is insufficient | 3.6, 4.4.2 | sales | `test_full_order_to_cash`, `test_invoice_blocked_when_stock_insufficient`, `test_invoice_posting_is_atomic` |
| FR-14 | Customer payments (partial allowed) and credit notes (returns to stock, VAT reversal) | 3.6 | sales | `test_full_order_to_cash`, `test_credit_note_returns_stock_and_reverses_revenue` |
| FR-15 | CRM: customers, contacts, interaction log (call/visit/email/complaint), feedback with CSAT 1–5 | 1.3.1, 1.3.2 | crm | `crm/tests/test_services.py` |
| FR-16 | Customer 360 page: orders, invoices, outstanding balance, interactions, average CSAT | 1.3.1, 3.5.2 | crm | `test_customer_360_aggregates`, `test_customer_360_shows_balance_and_csat` |
| FR-17 | Chart of accounts (seeded), journal entries that must balance, automatic postings from invoices, payments, credit notes, receipts and bills | 2.2, 3.6 | finance | `finance/tests/test_services.py` |
| FR-18 | Expenses with input VAT; VAT return summary (output − input, 5%) | 3.5.1 | finance | `test_expense_posts_vat_input_and_bank`, `test_vat_return_nets_output_and_input` |
| FR-19 | AR aging, AP aging, trial balance and profit & loss reports (UI and API) | 3.5.1 | finance | `test_trial_balance_balances_and_pnl`, `test_financial_report_endpoints` |
| FR-20 | HR: departments, employees, leave requests with approval workflow (Fri–Sat weekend excluded, balance checks, no self-approval) | 1.3.1 | hr | `hr/tests/test_services.py`, `test_leave_approval_ui` |
| FR-21 | PostgreSQL schema `reporting` with star-schema views: dim_date (2024–2027, Oman weekend/Ramadan/Eid/Khareef flags), dim_product, dim_customer, dim_supplier, dim_employee, dim_warehouse, fact_sales, fact_purchases, fact_inventory_daily, fact_payments, fact_expenses, fact_feedback (+ fact_interactions, fact_receivables) | 4.4.1, 4.5.2 | reports | `reports/tests/test_reporting.py` |
| FR-22 | Read-only PostgreSQL role `powerbi_reader` with SELECT on schema `reporting` only | 4.6, 5.1.1 | reports (migration + `setup_powerbi_reader`) | `test_powerbi_reader_is_read_only_on_reporting_schema` |
| FR-23 | RESTful reporting API for Power BI's Web connector (`/api/v1/reports/…`): token auth, date-range filters, pagination | 4.4.1, 4.5.2 | reports | `test_reporting_api_requires_permission_and_supports_token`, `test_every_reporting_endpoint_responds` |
| FR-24 | In-app dashboard: KPIs (revenue MTD/YTD, gross margin %, receivables, low-stock count, average CSAT) and charts (monthly sales, top 10 products, sales by city, cash in vs out) | 3.5.1, 4.5.1 | reports | `test_kpis`, `test_dashboard_charts`, `test_dashboard_and_builder_pages` |
| FR-25 | Custom report builder: dataset, date range, group-by, filters, preview; export to CSV, Excel and PDF | 3.5.1 | reports | `test_report_builder_groups_and_filters`, `test_exports` |
| FR-26 | Import wizard for customers, suppliers, products, opening stock and opening balances from CSV/Excel: upload → column mapping → validation and cleansing preview → dry run → commit | 5.1.3 | integrations | `integrations/tests/test_import_wizard.py` |
| FR-27 | Cleansing rules: trim/case normalisation, Oman phone format (+968), exact and fuzzy duplicate detection, missing required fields, negative quantities/amounts, date format normalisation; downloadable cleansing report (rows fixed, rejected and why) | 5.1.3 | integrations (`cleansing.py`) | `integrations/tests/test_cleansing.py`, `test_cleansing_report_and_mapping_rules` |
| FR-28 | Export endpoints (CSV/Excel) for all master data | 3.5.2 | integrations | `test_exports_csv_and_excel`, `test_export_permissions` |
| FR-30 | Realistic demo dataset (`make seed`): 18 months, 120 products, 40 suppliers, 300 customers in 6 cities, ~8,000 invoices with Ramadan/Eid, summer and Khareef seasonality, payment delays, feedback, employees and leave, stock-outs | 3.1, 5.1.4 | core (`seed_demo`) | `core/tests/test_seed_demo.py` |
| FR-31 | Monitoring page (Admin): uptime/availability, average and p95 response time, error rate, active users, DB size, last backup; same data at `/api/v1/reports/system-metrics/` and `reporting.fact_system_metrics_hourly` | 5.2.3 | monitoring | `monitoring/tests/test_monitoring.py` |
| FR-32 | Feasibility calculator: ROI, NPV, IRR, payback, discounted payback, 5-year TCO with Al Wadi defaults, cash-flow chart, PDF export, saved scenarios | 2.2.1–2.2.5 | feasibility | `feasibility/tests/test_formulas.py` |
| FR-29 | POS integration: `POST /api/v1/integrations/pos/sales/` with API-key auth and mandatory Idempotency-Key creates paid POS invoices without double posting | 3.5.2 | integrations | `integrations/tests/test_pos_and_exports.py` |

## Non-functional requirements

| ID | Requirement | Report § | Implementation | Tests |
|---|---|---|---|---|
| NFR-01 | Web UI usable on desktop, tablet and mobile | 2.3.5, 2.3.8, 4.4.1 | Bootstrap 5 responsive layout, off-canvas sidebar | UAT |
| NFR-02 | All traffic encrypted in transit (HTTPS, HTTP→HTTPS redirect, TLS to PostgreSQL) | 4.4.4, 4.6 | nginx TLS 1.2/1.3, HSTS; PostgreSQL `ssl=on` | UAT |
| NFR-03 | Account lockout after 5 failed logins (30 min) | 2.3.6 | django-axes | `test_security.py::test_account_locked_after_five_failed_logins` |
| NFR-04 | Passwords ≥ 12 characters; sessions expire after 30 minutes idle | 2.3.6 | Django password validators, session settings | `test_password_policy_requires_12_characters`, `test_session_idle_timeout_is_30_minutes` |
| NFR-05 | Health endpoint reports application and database status | 3.5.4, 5.2.3 | `/health/` | `core/tests/test_smoke.py` |
| NFR-06 | RESTful service layer with OpenAPI documentation | 4.4.1 | DRF `/api/v1/`, `/api/docs/` | `core/tests/test_module_api.py` |
| NFR-07 | Sensitive personal data encrypted at rest (employee civil ID, IBAN) and masked in UI/API | 4.6 | `core/fields.py` (Fernet) | `test_sensitive_fields_are_encrypted_at_rest`, `test_employee_api_masks_sensitive_fields` |
| NFR-08 | Cross-module postings are atomic (all-or-nothing) | 2.3.4 | `transaction.atomic()` in services | `test_invoice_posting_is_atomic`, `test_receipt_is_atomic` |
| NFR-09 | Money stored as exact decimals with 3 places (OMR baisa) | 4.4.2 | `DecimalField(14, 3)` | all finance tests |
| NFR-10 | Indexed relational schema with foreign keys | 4.4.2 | PostgreSQL 16, model indexes | migrations |
| NFR-11 | Daily compressed, checksummed (optionally encrypted) backups, 14-day retention, optional S3/Azure off-site copy | 5.2.2 | `scripts/backup.sh`, cron service | restore test in `docs/disaster_recovery.md` |
| NFR-12 | RPO 24 h, RTO 4 h with a tested restore procedure | 5.2.2 | `scripts/restore.sh`, `make restore` | `docs/disaster_recovery.md` §6, `test_last_backup_status` |
| NFR-13 | Performance monitoring of every request (count, response time, errors per endpoint) | 5.2.3, 2.3.2 | `monitoring.middleware` | `test_middleware_records_requests_per_endpoint` |
