# Legacy system sample files (dirty data for the migration demo)

These files simulate exports from Al Wadi Trading's old accounting/stock system. They are
intentionally messy to demonstrate the import wizard's cleansing rules (report §5.1.3).

| File | Import as | Problems planted |
|---|---|---|
| `suppliers_legacy.csv` | Suppliers | SHOUTING / lower-case names, exact duplicate code, fuzzy duplicate (`Al Marai Oman LLC` vs `almarai oman llc`), missing name, invalid phone and e-mail, negative payment terms |
| `customers_legacy.csv` | Customers | Mixed case and extra spaces, phones in 6 formats (normalised to `+968XXXXXXXX`), invalid phone, invalid e-mail, city spellings (`MCT`, `suhar`, `salala`, `Soor`, `bousher`…), exact and fuzzy duplicates in the same city, same name in a different city (kept as a branch), missing name/city, negative credit limit, non-numeric credit days, unknown customer type |
| `products_legacy.xlsx` | Products | Lower-case SKUs and spaces, duplicate SKU, missing SKU, negative cost, prices with "OMR" text, unit spellings (`pcs`, `Carton`, `kgs`, `tin`), category case/spacing, missing price, sale price below cost (warning) |
| `opening_stock_legacy.csv` | Opening stock | Warehouse names instead of codes, negative and blank quantities, unknown SKU, unknown warehouse, duplicate SKU/warehouse, mixed date formats (`31/12/2025`, `2025-12-31`, `31-Dec-2025`, `31.12.2025`, invalid `12.31.2025`), thousands separators |
| `opening_balances_legacy.csv` | Opening balances | Account codes with names appended, thousands separators, debit and credit on one line, unknown account, duplicate account |

**Demo order:** suppliers → customers → products → opening stock → opening balances.
Each import shows rows fixed, rows rejected (with the reason), and a downloadable cleansing report.

Regenerate the files with `docker compose run --rm web python sample_data/legacy/generate_legacy_files.py`.
