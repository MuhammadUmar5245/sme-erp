# Power BI Dashboard Specification

Report reference: §4.5.1 (dashboards with KPIs for sales, inventory, finance and customer satisfaction; reports by
geography and product line; trend analysis), §5.2.3 (Power BI showing ERP performance: downtime, usage, issues).

Theme: `sme_erp_theme.json` (primary teal `#0F4C5C`, accent orange `#E36414`, good `#2A9D8F`, bad `#C0392B`).
Canvas 16:9 (1280×720). Every page has a header bar with the page title, the Al Wadi logo placeholder, and the
**common slicers**: Date (dim_date Calendar hierarchy, "between" style), Region / City (dim_customer),
Warehouse (dim_warehouse). Sync the date slicer across pages (View → Sync slicers). Build a mobile layout for
pages 1 and 3 (View → Mobile layout) for managers on phones (report §2.3.5).

Measure names refer to `measures.dax`.

---

## Page 1 – Executive Overview

| Visual | Type | Fields | Formatting |
|---|---|---|---|
| Revenue YTD | Card (new card visual) | [Revenue YTD], reference label [YoY Growth %] | Conditional font colour on YoY: green ≥ 0, red < 0 |
| Revenue MTD | Card | [Revenue MTD] | |
| Gross Margin % | Card | [Gross Margin %] | Green ≥ 25 %, amber 20–25 %, red < 20 % |
| Receivables | Card | [Receivables Outstanding], label [Overdue %] | Red label if overdue % > 20 % |
| Low stock | Card | [Below Reorder Count] | Red if > 10 |
| Avg CSAT | Card | [Avg CSAT] | Green ≥ 4.0, amber 3.5–4.0, red < 3.5 |
| Monthly sales and forecast | Line and clustered column chart | X: dim_date[year_month]; columns [Total Revenue]; lines [Gross Margin], [Sales Forecast 3M MA] | Forecast line dashed |
| Sales by region | Filled map (or shape map of Oman governorates) | Location dim_customer[region]; colour saturation [Total Revenue] | Teal gradient |
| Top 10 products | Bar chart | dim_product[product_name], [Total Revenue], Top N filter = 10 by [Total Revenue] | Data labels in OMR |
| Cash in vs out | Clustered column | dim_date[year_month], [Cash In], [Cash Out]; line [Net Cash Flow] | Cash in green, out red |

Slicers: Date, Region. Drill-through to Page 2 from any product or region.

## Page 2 – Sales

| Visual | Type | Fields | Formatting |
|---|---|---|---|
| KPI strip | Cards | [Total Revenue], [Invoice Count], [Avg Order Value], [Units Sold], [Active Customers] | |
| Revenue trend | Line chart | dim_date[date] (Calendar hierarchy), [Total Revenue], [Revenue PY] | PY in grey |
| Seasonality | Column chart | dim_date[month_name], [Total Revenue]; legend dim_date[year] | Ramadan months highlighted (is_ramadan in tooltip) |
| Ramadan / Khareef impact | Clustered bar | dim_date[is_ramadan] and dim_date[is_khareef] (two visuals), [Total Revenue] per day = DIVIDE([Total Revenue], COUNTROWS(dim_date)) | |
| Sales by category | Treemap | dim_product[category_name] → product_name, [Total Revenue] | |
| Sales by customer type and city | Matrix | Rows dim_customer[customer_type]; columns dim_customer[city]; values [Total Revenue], [Gross Margin %] | Background colour scale on margin % (red → green) |
| Channel mix | Donut | fact_sales[source] (MANUAL / SO / POS), [Total Revenue] | |
| Customer ranking | Table | dim_customer[customer_name], city, [Total Revenue], [Gross Margin %], [YoY Growth %] | Data bars on revenue; icons on YoY |

Slicers: Date, Category, Customer type, Warehouse, Channel (source).

## Page 3 – Inventory (DirectQuery, automatic page refresh every 15 min)

| Visual | Type | Fields | Formatting |
|---|---|---|---|
| Inventory value | Card | [Inventory Value] | |
| Stock-outs today | Card | [Stock-out Count] | Red if > 0 |
| Below reorder | Card | [Below Reorder Count] | Amber if > 0 |
| Turnover / DIO | Cards | [Inventory Turnover], [Days Inventory Outstanding] | |
| Stock trend | Line chart | fact_inventory_daily[stock_date], [Inventory Value]; legend dim_warehouse[warehouse_code] | |
| Reorder list | Table | dim_product[sku], product_name, category_name, closing qty (SUM closing_qty at last date), reorder_level, [Below Reorder Count] | Row highlight red when closing qty ≤ 0, amber when ≤ reorder level |
| Stock by warehouse and category | Matrix | Rows category_name; columns warehouse_code; values [Inventory Value] | Colour scale |
| Daily movement | Column chart | stock_date, SUM qty_in, SUM qty_out | in green, out red |

Slicers: Warehouse, Category, Product.

## Page 4 – Finance

| Visual | Type | Fields | Formatting |
|---|---|---|---|
| KPI strip | Cards | [Revenue YTD], [Gross Margin], [Operating Expenses], [Net Cash Flow], [DSO] | DSO red if > 45 |
| Simple P&L | Matrix | Rows: Revenue / COGS / Gross margin / Expenses by fact_expenses[expense_category]; columns dim_date[year_month] | |
| Receivables aging | Stacked bar | fact_receivables[aging_bucket] (sort Current, 1-30, 31-60, 61-90, 90+), SUM balance_due | 90+ in red |
| Top overdue customers | Table | dim_customer[customer_name], [Overdue Receivables], MAX days_overdue | Red data bars |
| Cash flow | Waterfall | dim_date[year_month], [Net Cash Flow] | Increase green, decrease red |
| Expenses by category | Donut | fact_expenses[expense_category], [Operating Expenses] | |
| Payment behaviour | Column | dim_date[year_month], AVERAGE fact_payments[days_to_pay] (customer receipts) | Target line at 30 days |
| Purchases vs sales | Line | year_month, [Purchases], [COGS] | |

Slicers: Date, Region, Customer type.

## Page 5 – Customer / CRM

| Visual | Type | Fields | Formatting |
|---|---|---|---|
| KPI strip | Cards | [Avg CSAT], [Satisfied %], [Complaints], [Complaint Rate], [Active Customers] | CSAT and complaint thresholds as on page 1 |
| CSAT trend | Line | year_month, [Avg CSAT] | Constant line at 4.0 (target) |
| CSAT by city | Bar | dim_customer[city], [Avg CSAT] | Conditional colours (red < 3.5) |
| Score distribution | Column | fact_feedback[score], COUNTROWS | 1–2 red, 3 amber, 4–5 green |
| Interactions by type | Stacked column | year_month, COUNTROWS fact_interactions, legend interaction_type | Complaints red |
| Feedback comments | Table | feedback_date, customer_name, score, comment | Icons on score |
| Customer value vs satisfaction | Scatter | X [Total Revenue], Y [Avg CSAT], details customer_name, legend customer_type | Quadrant lines at averages |

Slicers: Date, City, Customer type, Channel (fact_feedback[channel]).

## Page 6 – System Health (ERP performance, report §5.2.3)

Source: `reporting.fact_system_metrics_hourly` (DirectQuery) and the API `GET /api/v1/reports/system-metrics/`
(Web source, for availability and last backup).

| Visual | Type | Fields | Formatting |
|---|---|---|---|
| Availability | Gauge | availability_pct (API), target 99.5 | Red < 99 |
| Avg / p95 response | Cards | [Avg Response ms], MAX p95_response_ms | Red if avg > 500 ms |
| Error rate | Card | [Error Rate %] | Red if > 1 % |
| Peak users | Card | [Peak Active Users] | |
| Last backup | Card / multi-row card | last_backup.status, last_backup.finished_at, last_backup.age_hours (API) | Red if age > 24 h (RPO) |
| Requests per hour | Area chart | hour_start, [Requests] | |
| Response time trend | Line | hour_start, [Avg Response ms], p95_response_ms | Constant line 500 ms |
| Errors | Column | hour_start, SUM error_count | Red |

Slicer: Date (last 7 days default, relative date filter).
