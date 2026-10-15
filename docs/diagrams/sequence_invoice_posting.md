# Sequence Diagram – Invoice Posting

Report reference: §3.6 (behavioural models: sequence diagrams). Shows `sales.services.create_invoice`, which is
called by the web UI, the REST API and the POS integration alike.

```mermaid
sequenceDiagram
    autonumber
    actor U as Sales officer
    participant N as nginx (TLS)
    participant V as Django view / API
    participant S as sales.services
    participant I as inventory.services
    participant F as finance.services
    participant DB as PostgreSQL
    participant A as audit (signals)

    U->>N: POST /sales/invoices/new/ (HTTPS)
    N->>V: forward (X-Forwarded-Proto: https)
    V->>V: check login, 2FA session, permission sales.add_invoice
    V->>S: create_invoice(customer, warehouse, lines, user)
    S->>DB: BEGIN (transaction.atomic)
    S->>I: lock_products(ids)
    I->>DB: SELECT ... FOR UPDATE (products)
    S->>I: check_availability(warehouse, quantities)
    I->>DB: SUM(quantity) per product in warehouse
    alt stock insufficient
        I-->>S: InsufficientStock
        S->>DB: ROLLBACK
        S-->>V: error
        V-->>U: form shows "Insufficient stock - need X, available Y"
    else stock available
        S->>DB: next_number("INV") (row lock on core_sequence)
        S->>DB: INSERT sales_invoice, sales_invoiceline (5% VAT per line)
        S->>DB: INSERT inventory_stockmovement (OUT, ref INV)
        S->>F: post_journal(AR, Sales, VAT output, COGS, Inventory)
        F->>F: validate: debits = credits, one side per line
        F->>DB: INSERT finance_journalentry + lines
        DB-->>A: post_save signals
        A->>DB: INSERT accounts_auditlog (user, IP, changes)
        S->>DB: UPDATE invoice totals, journal link
        S->>DB: COMMIT
        S-->>V: invoice
        V-->>U: redirect to invoice page ("Invoice posted")
    end
    Note over DB: reporting.fact_sales / fact_inventory_daily see the new rows immediately (DirectQuery)
```
