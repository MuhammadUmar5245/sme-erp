# Test Summary

Report reference: §4.2 and §5.1.2. Run with `make test` (Windows: `.\make.ps1 test`). The test suite runs against
PostgreSQL 16 in Docker (the same engine as production), including the `reporting` views and the
`powerbi_reader` role.

## 1. Results (15 October 2026)

| Module | Unit / integration tests | Failed | What is covered |
|---|---:|---:|---|
| accounts | 41 | 0 | Roles/permissions, menu and API RBAC, 2FA enrolment and verification, lockout, password policy, session timeout, audit log, user management |
| core | 48 | 0 | Health check, every module page for Admin, role access matrix, document forms, REST API flows, seed data consistency |
| inventory | 11 | 0 | Stock from movements, transfers, adjustments (ledger), weighted average cost, low stock, insufficient stock |
| purchasing | 8 | 0 | **Procure-to-pay integration** (PO → approve → partial/full receipt → bill → payments), atomicity, rules |
| sales | 10 | 0 | **Order-to-cash integration** (SO → invoice with 5% VAT → stock OUT → journal → payments), credit notes, stock blocking, atomicity |
| crm | 4 | 0 | Complaints, CSAT validation, Customer 360 aggregation |
| finance | 11 | 0 | Balanced journals, reversals, expenses, trial balance, P&L, VAT return, opening balances, cash flow |
| hr | 6 | 0 | Working days (Fri–Sat weekend), leave workflow and balances, no self-approval, encryption at rest |
| reports | 29 | 0 | Reporting views, dim_date calendar, read-only `powerbi_reader`, Power BI API (token, filters, paging), KPIs, report builder, exports |
| integrations | 65 | 0 | Cleansing rules, import wizard with the dirty legacy files, dry run, commit, cleansing report, exports, POS idempotency |
| monitoring | 9 | 0 | Request metrics, availability, p95, backup status/RPO, system-metrics API and reporting view |
| feasibility | 9 | 0 | NPV, IRR, payback, ROI, TCO against reference values; calculator, PDF, API |
| **Total** | **251** | **0** | Run time ≈ 2 minutes |

## 2. Code coverage

| Scope | Coverage (statements + branches) | Target |
|---|---:|---:|
| Business logic (`services.py`, `cleansing.py`, `importers.py`, `builder.py`, `audit.py`) | **93.3 %** | ≥ 80 % (enforced by `make test`) |
| Whole code base (excl. migrations and tests) | **91.3 %** | – |

The HTML report is written to `htmlcov/index.html`.

## 3. Integration tests of the business flows

| Flow | Test | Checks |
|---|---|---|
| Order-to-cash | `sales/tests/test_order_to_cash.py::test_full_order_to_cash` | Sales order totals, invoice VAT per line, due date, stock OUT movements, AR/Sales/VAT/COGS postings, partial and final payment, AR aging, trial balance |
| Procure-to-pay | `purchasing/tests/test_procure_to_pay.py::test_full_procure_to_pay` | Approval, partial receipt, stock IN, Inventory/GRNI, bill (GRNI/VAT input/AP), partial and final payments, AP aging, trial balance |
| Atomicity | `test_invoice_posting_is_atomic`, `test_receipt_is_atomic` | A failure in the ledger rolls back the invoice/receipt and the stock movements |
| Over HTTP | `core/tests/test_module_api.py` | The same flows through the REST API with role-based access |

## 4. Load test (50 concurrent users)

`loadtest/locustfile.py`: 40 office users (log in, dashboard, analytics, invoice list, product search, stock levels,
Customer 360, AR aging) and 10 Power BI API clients (paged `fact-sales`, KPIs, inventory). 3 minutes against the
full HTTPS stack (nginx → gunicorn with 3 workers → PostgreSQL) on a Windows laptop with Docker Desktop, with the
complete 18-month demo dataset (8,009 invoices).

| Metric | Result |
|---|---|
| Requests | 3,364 (18.7 req/s) |
| Failures | **0 (0.00 %)** |
| Median response time | **73 ms** |
| 90th / 95th percentile | 520 ms / 1,200 ms |
| Slowest endpoint | `fact-inventory-daily` API (median 2.3 s; the view rebuilds daily stock with a window function) |

All requests were authenticated (verified in `monitoring_requestmetric`). Recommendation from the test: for larger
datasets, turn `reporting.fact_inventory_daily` into a materialized view refreshed nightly, and add gunicorn
workers or instances (report §5.2.3 scalability). Raw results: `loadtest/results/run_stats.csv`.

## 5. Other verification

| Area | Evidence |
|---|---|
| Backup and restore | Restore drill on 15 Oct 2026: restore 3 s, data verified (`docs/disaster_recovery.md` §6) |
| TLS | HTTP→HTTPS redirect, TLS 1.2/1.3 on nginx; PostgreSQL SSL connection reported `TLSv1.3` |
| Power BI | API paging (14,998 sales lines) with the Power BI token; `powerbi_reader` limited to schema `reporting` |
| UAT | 48 cases in `docs/testing/uat_test_cases.md` (formal execution by business users at sign-off) |
