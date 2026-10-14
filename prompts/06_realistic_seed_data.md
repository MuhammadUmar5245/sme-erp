# Phase 6 — Realistic seed data

Create a management command `seed_demo` (deterministic, random seed 42) for Al Wadi Trading
Distributors: 18 months of data ending today; ~120 products in 8 categories;
40 suppliers; 300 customers across Muscat, Seeb, Sohar, Salalah, Nizwa, Sur;
~8,000 invoices with seasonality (Ramadan/Eid spikes, slow summer months June–August, Khareef season boost in Salalah);
realistic payment delays for AR aging; feedback records; employees and leave records;
a few stock-outs. `make seed` must reset and reload. Print summary counts at the end.
