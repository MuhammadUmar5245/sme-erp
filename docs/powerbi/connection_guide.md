# Power BI Connection Guide

Report reference: §4.4.1 (Power BI reporting, RESTful service layer), §4.5 (data analysis with Power BI),
§4.5.2 (real-time reporting), §4.4.4/§4.6 (encrypted connections), §5.1.1 (Power BI data connections),
§5.1.2 (Power BI testing).

Power BI can reach the ERP in two ways. Both are read-only and both are encrypted with TLS.

| | Option A: PostgreSQL (recommended) | Option B: Web/API connector |
|---|---|---|
| Source | Schema `reporting` (views `dim_*`, `fact_*`) | `https://<server>/api/v1/reports/<dataset>/` |
| Credentials | Database role `powerbi_reader` (SELECT on `reporting` only) | API token of the service user `powerbi@alwadi.om` |
| Modes | Import **or DirectQuery** (near real time) | Import only (scheduled refresh) |
| Best for | Internal network / VPN, on-premises data gateway | When port 5432 cannot be opened, cloud-only setups |

## 1. Prerequisites

1. Power BI Desktop (Windows) – latest version.
2. The ERP running with demo data: `make up` and `make seed`.
3. The `powerbi_reader` password = `POWERBI_READER_PASSWORD` in `.env`. Rotate it with
   `docker compose run --rm web python manage.py setup_powerbi_reader --password <new>`.
4. The API token printed by `make seed` (or create one: Django admin → Tokens → add for `powerbi@alwadi.om`).

## 2. Option A – PostgreSQL connector (Npgsql)

Power BI Desktop includes the Npgsql provider (recent versions). On older versions install
Npgsql 4.0.x with the "GAC installation" option, then restart Power BI.

1. **Get data → PostgreSQL database**.
2. Server: `localhost:5432` (the `db` service publishes port 5432; in production use the private DNS name or
   VPN address, never an open internet port). Database: `sme_erp`.
3. **Data connectivity mode**:
   - **DirectQuery** for `fact_sales`, `fact_inventory_daily`, `fact_receivables` and `fact_system_metrics_hourly`
     – each visual queries PostgreSQL live, so stock levels and sales are near real time (report §4.5.2).
   - **Import** for the dimensions (`dim_*`) and slow-moving facts (`fact_expenses`, `fact_feedback`) – faster visuals.
   - Mixing both in one model ("composite model") is supported: set dimensions to **Dual** storage mode.
4. Credentials: **Database**, user `powerbi_reader`, password from `.env`.
5. Encryption: keep "Encrypt connection" ticked. PostgreSQL runs with SSL (`ssl=on`). With the local self-signed
   certificate, either import `certs/server.crt` into *Trusted Root Certification Authorities* of the Windows user,
   or (local demo only) untick *Encrypt connection*. In production use a certificate from a trusted CA.
6. In the navigator expand **reporting** and select all `dim_*` and `fact_*` views. Do not select anything from
   `public` – the role has no access to it.
7. Build the model as described in [model.md](model.md), add [measures.dax](measures.dax), apply the theme
   [sme_erp_theme.json](sme_erp_theme.json) (*View → Themes → Browse for themes*).

Security notes: `powerbi_reader` is `NOSUPERUSER NOCREATEDB NOCREATEROLE`, has `default_transaction_read_only = on`,
a 120 s statement timeout and SELECT only on schema `reporting`. Views hide encrypted HR fields and salaries.

## 3. Option B – Web / API connector with a token

1. **Get data → Blank query → Advanced editor**, paste [powerquery_api.m](powerquery_api.m).
2. Create the parameters `BaseUrl` (e.g. `https://localhost`), `ApiToken` (the token) and `DateFrom`
   (e.g. `2025-01-01`), as described at the top of the file.
3. Invoke `GetDataset("fact-sales")`, `GetDataset("dim-product")`, … for each dataset
   (list: `GET /api/v1/reports/`). Each call pages through the API with `page_size=5000`.
4. Credentials prompt for `BaseUrl`: choose **Anonymous** (the token is sent in the `Authorization` header).
5. Set data types (the API returns money as text to avoid rounding): the M file contains a typed example for
   `fact-sales`.

The same token can read `GET /api/v1/reports/kpis/` and `GET /api/v1/reports/system-metrics/` for the
System Health page.

## 4. Publishing and scheduled refresh (Power BI Service)

1. **Publish** the report to a workspace (Power BI Pro or Premium Per User licence).
2. Install the **on-premises data gateway** (standard mode) on a Windows machine that can reach the database
   (same VNet/VPN as the ERP server). Sign in with the organisation account and register the gateway.
3. Power BI Service → **Settings → Manage connections and gateways → New**: data source type *PostgreSQL*,
   server `db-host:5432`, database `sme_erp`, user `powerbi_reader`. For Option B add a *Web* source for `BaseUrl`.
4. Dataset settings → **Gateway connection** → map the data sources.
5. **Scheduled refresh** (Import tables): e.g. 07:00, 12:00, 16:00 Asia/Muscat (up to 8/day with Pro).
   DirectQuery tables need no refresh; set *Automatic page refresh* to 5–15 minutes on the Inventory page.
6. Row-level security (optional): create roles on `dim_warehouse[warehouse_code]` (e.g. Sohar branch manager sees `SOH` only).

## 5. Testing the integration (report §5.1.2 "Power BI Testing")

| Check | How | Expected |
|---|---|---|
| Row counts | Card with `COUNTROWS(fact_sales)` vs `SELECT COUNT(*) FROM reporting.fact_sales` or API `count` | Equal |
| Revenue reconciles | `[Revenue YTD]` vs ERP dashboard KPI "Revenue YTD" | Equal (both net of VAT and returns) |
| Near real time | Post an invoice in the ERP, refresh the DirectQuery visual | New invoice visible within seconds |
| Security | Try `SELECT * FROM public.sales_invoice` as `powerbi_reader` | `permission denied` |
| Encryption | `SELECT ssl, version FROM pg_stat_ssl WHERE pid = pg_backend_pid();` as `powerbi_reader` | `t`, TLSv1.3 |
