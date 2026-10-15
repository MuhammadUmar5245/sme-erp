# Data Flow Diagrams

Report reference: §3.6 (functional models: data flow diagrams).
Notation: rectangles = external entities, rounded boxes = processes, cylinders = data stores.

## DFD Level 0 (context diagram)

```mermaid
flowchart LR
    Customer[Customer]
    Supplier[Supplier]
    Staff[Al Wadi staff<br/>7 roles]
    POS[POS terminal]
    Legacy[Legacy system files]
    PBI[Power BI]
    Bank[Bank / Tax Authority]

    ERP((0<br/>SME-ERP))

    Customer -- orders, payments, feedback --> ERP
    ERP -- tax invoices, statements --> Customer
    ERP -- purchase orders, payments --> Supplier
    Supplier -- deliveries, supplier invoices --> ERP
    Staff -- transactions, approvals, master data --> ERP
    ERP -- dashboards, reports, alerts --> Staff
    POS -- shop sales --> ERP
    ERP -- invoice numbers --> POS
    Legacy -- CSV / Excel extracts --> ERP
    ERP -- cleansing reports --> Staff
    ERP -- reporting views / API data --> PBI
    ERP -- VAT return figures, payment files --> Bank
```

## DFD Level 1

```mermaid
flowchart TB
    Customer[Customer]
    Supplier[Supplier]
    Staff[Staff]
    POS[POS terminal]
    Legacy[Legacy files]
    PBI[Power BI]

    P1(1.0 Manage access<br/>accounts)
    P2(2.0 Sell and collect<br/>crm + sales)
    P3(3.0 Buy and pay<br/>purchasing)
    P4(4.0 Control stock<br/>inventory)
    P5(5.0 Account and report<br/>finance)
    P6(6.0 Manage people<br/>hr)
    P7(7.0 Analyse<br/>reports)
    P8(8.0 Integrate and migrate<br/>integrations)

    D1[(D1 Users, roles, audit log)]
    D2[(D2 Customers, interactions, feedback)]
    D3[(D3 Sales orders, invoices, payments)]
    D4[(D4 Suppliers, POs, receipts, bills)]
    D5[(D5 Products, stock movements)]
    D6[(D6 Accounts, journal entries)]
    D7[(D7 Employees, leave)]
    D8[(D8 Reporting schema<br/>dim_* / fact_*)]

    Staff -- credentials, 2FA --> P1
    P1 <--> D1
    Customer -- orders, payments --> P2
    P2 -- invoices --> Customer
    P2 <--> D2
    P2 <--> D3
    P2 -- stock OUT --> P4
    P2 -- AR, sales, VAT, COGS postings --> P5
    Supplier -- deliveries, bills --> P3
    P3 -- POs, payments --> Supplier
    P3 <--> D4
    P3 -- stock IN --> P4
    P3 -- inventory, GRNI, AP postings --> P5
    P4 <--> D5
    P5 <--> D6
    Staff -- leave requests --> P6
    P6 <--> D7
    POS -- sales --> P8
    Legacy -- extracts --> P8
    P8 -- clean master data --> D2 & D4 & D5
    P8 -- POS invoices --> P2
    P8 -- opening balances --> P5
    D2 & D3 & D4 & D5 & D6 & D7 --> D8
    D8 --> P7
    P7 -- KPIs, reports, exports --> Staff
    D8 -- DirectQuery / API --> PBI
```
