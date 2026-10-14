# Phase 4 — Reporting layer and Power BI service API

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
