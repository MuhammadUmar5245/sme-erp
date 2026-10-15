# Use Case Diagram

Report reference: §3.6 (functional models: use case diagrams). Mermaid has no UML use-case notation, so actors
are drawn as stadium nodes and use cases as rounded boxes inside the system boundary.

```mermaid
flowchart LR
    Admin([Admin])
    Manager([Manager])
    Accountant([Accountant])
    Sales([Sales officer])
    Store([Storekeeper])
    HR([HR officer])
    Viewer([Viewer])
    POS([POS system])
    PBI([Power BI])

    subgraph ERP["SME-ERP (Al Wadi Trading & Distribution)"]
        UC1(Log in with 2FA)
        UC2(Manage users, roles and audit log)
        UC3(Monitor system and backups)
        UC4(Manage products, warehouses, stock movements)
        UC5(Create and approve purchase orders)
        UC6(Receive goods)
        UC7(Record supplier bills and payments)
        UC8(Manage customers, contacts, interactions)
        UC9(Create sales orders and invoices)
        UC10(Record customer payments and credit notes)
        UC11(Post journals and expenses)
        UC12(Run VAT, aging, trial balance, P&L)
        UC13(Manage employees and leave)
        UC14(Approve leave)
        UC15(View dashboards and build reports)
        UC16(Import legacy data with cleansing)
        UC17(Export master data)
        UC18(Calculate ROI / NPV / IRR / TCO)
        UC19(Post POS sales via API)
        UC20(Read reporting views / API)
        UC21(Rate the system and get support)
    end

    Admin --- UC1 & UC2 & UC3 & UC16
    Manager --- UC1 & UC5 & UC14 & UC15 & UC18 & UC17
    Accountant --- UC1 & UC7 & UC10 & UC11 & UC12 & UC16 & UC18
    Sales --- UC1 & UC8 & UC9 & UC10
    Store --- UC1 & UC4 & UC6
    HR --- UC1 & UC13 & UC14
    Viewer --- UC1 & UC15
    Viewer --- UC21
    Sales --- UC21
    POS --- UC19
    PBI --- UC20
```

| Actor | Main goals |
|---|---|
| Admin | Users and roles, audit log, monitoring and backups, data migration (has every permission) |
| Manager | Approve purchases and leave, follow KPIs, feasibility |
| Accountant | Bills, payments, journals, expenses, VAT and financial reports |
| Sales officer | Customers and CRM, orders, invoices, receipts |
| Storekeeper | Stock, transfers, adjustments, goods receipts |
| HR officer | Employees, departments, leave |
| Viewer | Read-only business data and dashboards |
| POS system | Sends completed shop sales (API key + idempotency key) |
| Power BI | Reads the `reporting` schema (powerbi_reader) or the reporting API (token) |
