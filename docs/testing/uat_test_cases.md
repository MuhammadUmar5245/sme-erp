# User Acceptance Test (UAT) Cases

Report reference: §4.2 (testing at the end of each sprint), §5.1.2 (unit, integration, UAT, Power BI testing).

**Environment:** `https://localhost` after `make up` and `make seed` (Al Wadi demo data). Demo password for all
users: `AlWadi-Demo-2026!`. Admin and Accountant must enrol 2FA (Google/Microsoft Authenticator) at first login.

**How to read the "Actual result" and "Status" columns.** Each case is backed by an automated test or a recorded live check (named in the Actual column). Status
**Pass (dev)** means it passed that verification; **To run** means it still needs a manual check. Formal UAT is the business users executing the steps themselves
and replacing "Pass (dev)" with their own result, tester initials and date. The project sign-off
(`docs/project_signoff.md`) requires that.

| ID | Module | Role | Preconditions | Steps | Expected result | Actual result | Status |
|---|---|---|---|---|---|---|---|
| UAT-01 | Security | Viewer | Demo data loaded | Open `http://localhost` | Browser is redirected to `https://localhost`; padlock shows TLS | Redirect 301 → HTTPS (live check) | Pass (dev) |
| UAT-02 | Security | Viewer | – | Log in as `viewer@alwadi.om` with the demo password | Dashboard opens; menu shows only business modules, no Administration | `test_menu_hides_administration_for_viewer` | Pass (dev) |
| UAT-03 | Security (RBAC) | Viewer | Logged in | Open Sales → Invoices, then try `/sales/invoices/new/` | List is visible; creating an invoice returns 403 Forbidden | `test_role_access_to_pages[Viewer-…]` | Pass (dev) |
| UAT-04 | Security (RBAC) | Storekeeper | Logged in as `store@alwadi.om` | Try to open Sales → New invoice and HR → Employees | Both refused (403); Inventory pages work | `test_role_access_to_pages[Storekeeper-…]`, `test_api_rbac` | Pass (dev) |
| UAT-05 | Security (2FA) | Admin | First login of `admin@alwadi.om` | Log in; scan the QR code; enter the 6-digit code | 2FA is mandatory; after a valid code the dashboard opens | `test_enrolment_with_qr_and_valid_code_activates_2fa` | Pass (dev) |
| UAT-06 | Security (2FA) | Accountant | 2FA enrolled | Log out, log in with password only, then a wrong code, then the right code | Wrong code rejected; correct code gives access | `test_user_with_device_must_verify_after_password`, `test_enrolment_rejects_wrong_code` | Pass (dev) |
| UAT-07 | Security (lockout) | Any | – | Enter a wrong password 5 times for `sales@alwadi.om`, then the right one | "Account temporarily locked" page; audit log shows failed logins | `test_account_locked_after_five_failed_logins` | Pass (dev) |
| UAT-08 | Security (lockout) | Admin | UAT-07 done | Administration → Users → sales@ → Unlock; user logs in | Login succeeds again | `test_admin_can_unlock_account` | Pass (dev) |
| UAT-09 | Security | Any | Logged in | Leave the browser idle for 31 minutes, then click a menu item | Session expired; login page shown | `test_session_idle_timeout_is_30_minutes` | Pass (dev) |
| UAT-10 | Security (audit) | Admin | – | Edit a customer's credit limit as Manager; open Administration → Audit log as Admin | Entry with user, IP, time and before/after values | `test_create_update_delete_are_logged_with_changes`, `test_request_user_and_ip_are_captured` | Pass (dev) |
| UAT-11 | Administration | Admin | – | Create user `newclerk@alwadi.om`, role SalesOfficer, password of 8 characters | Rejected: at least 12 characters; with 12+ the user is created with the role | `test_create_user_service_rejects_weak_password`, `test_user_form_ui_creates_user` | Pass (dev) |
| UAT-12 | Inventory | Storekeeper | – | Inventory → Products → New: SKU, category, prices, reorder level | Product saved; appears in search and in the API | `test_every_module_page_renders_for_admin`, inventory API tests | Pass (dev) |
| UAT-13 | Inventory | Storekeeper | Product with stock | Stock movements → New → Transfer 10 units MCT → SOH | Two movements with one TRF number; stock levels move 10 units | `test_transfer_moves_stock_between_warehouses` | Pass (dev) |
| UAT-14 | Inventory | Storekeeper | – | Record an adjustment of −3 with reason "Damaged" | Stock reduced; journal posted to Inventory adjustments | `test_adjustment_posts_to_ledger` | Pass (dev) |
| UAT-15 | Inventory | Manager | Demo data | Open the dashboard | Low-stock list shows items at/below reorder level (incl. out-of-stock items) | `test_dashboard_lists_low_stock` | Pass (dev) |
| UAT-16 | Purchasing | Manager | Supplier and products exist | Create PO with 2 lines; Approve | Status Draft → Approved; Storekeeper cannot approve | `test_po_ui_flow`, `test_procure_to_pay_over_api` | Pass (dev) |
| UAT-17 | Purchasing | Storekeeper | Approved PO | Receive goods: part of one line, then the rest | Partial receipt keeps PO Approved; full receipt → Received; stock increases | `test_full_procure_to_pay` | Pass (dev) |
| UAT-18 | Purchasing | Accountant | Received PO | Record supplier bill, then pay part and the balance | Bill Unpaid → Partially paid → Paid; AP returns to zero | `test_full_procure_to_pay` | Pass (dev) |
| UAT-19 | Sales | SalesOfficer | Customer, stock | Create sales order, confirm, create invoice | Invoice with 5% VAT per line; stock reduced; order Invoiced | `test_full_order_to_cash` | Pass (dev) |
| UAT-20 | Sales | SalesOfficer | Product with 4 units | Create invoice for 9 units | Blocked with "Insufficient stock"; nothing posted | `test_invoice_ui_posts_and_blocks_on_stock` | Pass (dev) |
| UAT-21 | Sales | Accountant | Open invoice | Receive a partial payment, then the rest | Status Partially paid → Paid; AR aging updates | `test_full_order_to_cash` | Pass (dev) |
| UAT-22 | Sales | Accountant | Invoice | Issue credit note for 4 of 10 units (return to stock) | Credit note posts reversal of sales and VAT; stock +4; balance reduced | `test_credit_note_returns_stock_and_reverses_revenue` | Pass (dev) |
| UAT-23 | Sales | SalesOfficer | Invoice | Click Print | Printable tax invoice with company VATIN, VAT 5% column and totals | `test_every_module_page_renders_for_admin` (invoice_print) | Pass (dev) |
| UAT-24 | CRM | SalesOfficer | Demo data | Open a customer (Customer 360) | Shows sales, outstanding, overdue, CSAT, contacts, interactions | `test_customer_360_aggregates`, `test_customer_360_shows_balance_and_csat` | Pass (dev) |
| UAT-25 | CRM | SalesOfficer | Customer | Log a complaint; mark it resolved | Complaint is Open, then Closed; open-complaint count changes | `test_complaints_open_and_can_be_closed` | Pass (dev) |
| UAT-26 | CRM | SalesOfficer | Customer | Record feedback with score 6, then 4 | 6 rejected (1–5 only); 4 saved; average CSAT updates | `test_feedback_score_validated` | Pass (dev) |
| UAT-27 | Finance | Accountant | – | New manual journal: Dr 100 / Cr 90 | Rejected "does not balance"; balanced entry posts | `test_manual_journal_ui_rejects_unbalanced` | Pass (dev) |
| UAT-28 | Finance | Accountant | – | Record expense: fuel OMR 100 + 5% VAT, paid from bank | Expense posted: Dr 6300, Dr VAT input 5, Cr Bank 105 | `test_expense_posts_vat_input_and_bank` | Pass (dev) |
| UAT-29 | Finance | Accountant | Demo data | Financial reports → VAT return for last quarter | Output VAT, input VAT and net payable shown | `test_vat_return_nets_output_and_input` | Pass (dev) |
| UAT-30 | Finance | Accountant | Demo data | Trial balance; P&L YTD; AR and AP aging | Trial balance "Balanced"; aging buckets Current/1-30/31-60/61-90/90+ | `test_trial_balance_balances_and_pnl`, `test_financial_report_endpoints` | Pass (dev) |
| UAT-31 | HR | HROfficer | Employee | Submit annual leave Sun–Thu next week | 5 working days (Fri–Sat excluded); status Pending | `test_working_days_exclude_friday_and_saturday` | Pass (dev) |
| UAT-32 | HR | Manager | Pending leave | Approve leave; employee tries to approve own request | Approved; self-approval refused | `test_submit_and_approve_leave`, `test_cannot_approve_own_request` | Pass (dev) |
| UAT-33 | HR | HROfficer | Employee with civil ID | Open employee detail | Civil ID and IBAN masked (••••5678); stored encrypted in DB | `test_sensitive_fields_are_encrypted_at_rest` | Pass (dev) |
| UAT-34 | Reports | Manager | Demo data | Reports → Analytics dashboard | KPI cards and 4 charts (monthly trend, top 10 products, by city, cash in/out) | `test_dashboard_and_builder_pages`, `test_kpis` | Pass (dev) |
| UAT-35 | Reports | Manager | Demo data | Report builder: Sales by City and Category, Salalah only; export Excel and PDF | Preview shows grouped totals; files download and open | `test_report_builder_groups_and_filters`, `test_exports` | Pass (dev) |
| UAT-36 | Power BI | Viewer (Power BI) | Token for powerbi@ | Power BI Desktop → Web connector → `/api/v1/reports/fact-sales/` (powerquery_api.m) | All pages load; row count equals the API `count` | `test_reporting_api_requires_permission_and_supports_token`; live check: 14,998 rows | Pass (dev) |
| UAT-37 | Power BI | IT | `powerbi_reader` password | Power BI → PostgreSQL connector, schema `reporting` (DirectQuery) | Views load; operational tables are not accessible | `test_powerbi_reader_is_read_only_on_reporting_schema` | Pass (dev) |
| UAT-38 | Data migration | Accountant | – | Import `sample_data/legacy/customers_legacy.csv`: map columns, validate | Preview shows clean/fixed/rejected rows with reasons (phones +968, cities, duplicates) | `test_customer_import_cleanses_and_rejects` | Pass (dev) |
| UAT-39 | Data migration | Accountant | UAT-38 | Dry run, then Commit; download cleansing report | Dry run saves nothing; commit creates only valid rows; CSV report lists fixes and rejections | `test_customer_import_cleanses_and_rejects`, `test_wizard_ui_flow` | Pass (dev) |
| UAT-40 | Data migration | Admin | Products imported | Import opening stock then opening balances samples | Negative/unknown rows rejected; stock and GL balances posted | `test_products_then_opening_stock_and_balances` | Pass (dev) |
| UAT-41 | Integration (POS) | IT | POS API key | POST a sale twice with the same Idempotency-Key | One invoice only; second call returns the same invoice (Idempotent-Replayed) | `test_idempotent_replay_does_not_double_post` | Pass (dev) |
| UAT-42 | Integration | Manager | – | Data & integration → Exports → Products (Excel) | Excel file with all products downloads | `test_exports_csv_and_excel` | Pass (dev) |
| UAT-43 | Backup/DR | Admin | Stack running | `make backup`; check System monitoring → Last backup | New timestamped backup; status Success, age < 24 h | Live: `sme_erp_20261015_110119.dump` 3.9 MB, success | Pass (dev) |
| UAT-44 | Backup/DR | Admin | Backup exists | Change a record, then `make restore FILE=latest` and type RESTORE | Data back to backup state; app healthy; trial balance balanced | Live drill 2026-10-15 (docs/disaster_recovery.md §6): restore 3 s | Pass (dev) |
| UAT-45 | Monitoring | Admin | Some usage | Open Administration → System monitoring | Availability, avg/p95 response, error rate, active users, DB size, last backup | `test_monitoring_page_admin_only`, `test_summary_figures` | Pass (dev) |
| UAT-46 | Feasibility | Accountant | – | Reports → Feasibility; change discount rate to 12%; export PDF | NPV/IRR/ROI/payback/TCO recalculate; PDF downloads with chart | `test_calculator_page_api_and_saved_scenarios` | Pass (dev) |
| UAT-47 | Usability | Any | – | Open the app on a phone (or browser at 375 px width) | Sidebar collapses into a menu button; tables scroll horizontally; forms stack | Built with Bootstrap responsive grid and an off-canvas sidebar below 992 px; not yet checked on a real phone/tablet | To run |
| UAT-48 | Performance | – | Demo data | Run `loadtest/locustfile.py` with 50 users | No failed requests; median response < 200 ms | Live: 3,364 requests, 0 failures, median 73 ms (docs/testing/test_summary.md) | Pass (dev) |
