# Phase 5 — Data migration and integrations

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
