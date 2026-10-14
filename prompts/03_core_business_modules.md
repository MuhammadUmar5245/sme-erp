# Phase 3 — Core business modules

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
