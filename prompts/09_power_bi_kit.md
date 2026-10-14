# Phase 9 — Power BI kit

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
