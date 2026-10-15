# SME-ERP User Manual – Al Wadi Trading & Distribution LLC

Report reference: §5.1.5 (user manuals for training), §2.3.9 (ease of use).

Screenshots are referenced as placeholders `![…](screenshots/<name>.png)`; capture them from the seeded demo
system (1366×768 desktop, plus the `-mobile` ones at 390×844) and save them in `docs/screenshots/`.

## 1. Getting started (all users)

1. Open **https://<erp-address>** (demo: https://localhost). The connection is always encrypted.
2. Sign in with your work e-mail and password (at least 12 characters).
   ![Login page](screenshots/01-login.png)
3. **Two-factor authentication.** Admin and Accountant must set it up at first login; others can switch it on in
   *My profile & 2FA*. Install Google or Microsoft Authenticator, scan the QR code, type the 6-digit code.
   ![2FA enrolment](screenshots/02-2fa-setup.png)
4. After 5 wrong passwords the account is locked for 30 minutes (ask the Admin to unlock it). After 30 minutes
   without activity you are logged out automatically.
5. **Layout.** The menu on the left lists only the modules your role may use. On a phone or tablet tap
   **☰** to open it. The top-right menu has *My profile & 2FA* and *Log out*.
   ![Dashboard](screenshots/03-dashboard.png) ![Mobile menu](screenshots/03-dashboard-mobile.png)
6. **Lists** have a search box (results update while you type), filters, and pages of 25 rows. Click the first
   column to open a record. **Forms** show errors next to the field.
7. **Help & support** (menu *Help*): help-desk contacts, response times, and a form to rate the system or report a problem.
   ![Help and support](screenshots/04-support.png)

## 2. Admin

| Task | Where | Steps |
|---|---|---|
| Create a user | Administration → Users → *New user* | E-mail, name, department, tick the role(s), password (12+). Admin role also grants Django admin access. |
| Reset 2FA / unlock | Users → open user | *Reset 2FA* (lost phone) or *Unlock* (after 5 failed logins). |
| Audit log | Administration → Audit log | Filter by action, model, date; open an entry to see before/after values. |
| System monitoring | Administration → System monitoring | Availability, response times, errors, active users, DB size, last backup (must be < 24 h old). |
| User evaluation | Administration → User evaluation | Average rating per area, open problems; *Resolve* when fixed. |
| POS API keys | Data & integration → POS API keys | Create a key per terminal (shown once), revoke lost keys. |
| Backups | Command line | `make backup`, `make restore FILE=latest` – see `docs/disaster_recovery.md`. |

![Users](screenshots/10-admin-users.png) ![Audit log](screenshots/11-admin-audit.png) ![Monitoring](screenshots/12-admin-monitoring.png)

## 3. Manager

| Task | Where | Steps |
|---|---|---|
| Follow KPIs | Dashboard / Reports → Analytics | Revenue MTD/YTD, margin, receivables, low stock, CSAT and four charts. |
| Approve purchase orders | Purchasing → Purchase orders → filter *Draft* | Open the PO, check lines and totals, click **Approve**. |
| Approve leave | HR → Leave requests → filter *Pending* | Open, check the balance, **Approve** or **Reject** with a note. |
| Report builder | Reports → Report builder | Choose dataset (Sales, Purchases, Inventory, Payments, Expenses, CSAT), dates, group-by, filters → *Run*; export CSV/Excel/PDF. |
| Feasibility | Reports → Feasibility | Change assumptions, see NPV/IRR/ROI/payback/TCO, *Export PDF*, save scenarios. |

![Analytics](screenshots/20-manager-analytics.png) ![Report builder](screenshots/21-manager-report-builder.png) ![Feasibility](screenshots/22-manager-feasibility.png)

## 4. Accountant

| Task | Where | Steps |
|---|---|---|
| Supplier bill | Purchasing → PO (status *Received*) → **Record supplier bill** | Enter the supplier's invoice number and date → posts AP and VAT input. |
| Pay a supplier | Purchasing → Supplier bills → bill → **Record payment** | Amount (partial allowed), date, method. |
| Receive a customer payment | Sales → Invoices → invoice → **Receive payment** | Amount (partial allowed), method, reference. |
| Credit note | Invoice → **Credit note** | Quantity per line, reason, *Return goods to stock*. |
| Expense | Finance → Expenses → *New* | Expense account, payee, net amount, VAT %, paid from cash/bank. |
| Manual journal | Finance → Journal entries → *New* | Lines must balance (debits = credits). |
| VAT return, aging, TB, P&L | Finance → Financial reports | Pick the tab and the period; amounts in OMR. |
| Opening balances import | Data & integration → Import wizard | See §8. |

![Invoice](screenshots/30-accountant-invoice.png) ![VAT return](screenshots/31-accountant-vat.png) ![AR aging](screenshots/32-accountant-ar-aging.png)

## 5. Sales officer

| Task | Where | Steps |
|---|---|---|
| New customer | CRM → Customers → *New* | Code is proposed automatically; set city, terms, credit limit. |
| Customer 360 | CRM → Customers → customer | Sales, balance, overdue, CSAT, contacts, interactions; buttons for invoice, interaction, feedback. |
| Sales order | Sales → Sales orders → *New* | Customer, warehouse, lines (blank price = list price). Then **Confirm** and **Create invoice**. |
| Direct invoice | Sales → Invoices → *New* | Posts immediately; refused if stock is insufficient in the chosen warehouse. |
| Print invoice | Invoice → **Print** | Tax invoice with VATIN and 5 % VAT. |
| Log a visit/complaint | CRM → Interactions → *New* | Complaints stay *Open* until marked resolved. |

![Customer 360](screenshots/40-sales-customer-360.png) ![New invoice](screenshots/41-sales-new-invoice.png) ![Mobile invoice list](screenshots/42-sales-invoices-mobile.png)

## 6. Storekeeper

| Task | Where | Steps |
|---|---|---|
| Stock levels | Inventory → Stock levels | Per warehouse (MCT, SOH); tick *Low stock only*. |
| Receive goods | Purchasing → PO (*Approved*) → **Receive goods** | Enter received quantities (partial allowed) → stock IN. |
| Transfer / adjust | Inventory → Stock movements → *New* | Transfer between warehouses, or adjustment (+/−) with a reason (posted to the ledger). |
| Products | Inventory → Products | Search by SKU/name; edit reorder levels. |

![Stock levels](screenshots/50-store-stock-levels.png) ![Receive goods](screenshots/51-store-receive.png)

## 7. HR officer

| Task | Where | Steps |
|---|---|---|
| Employees | HR → Employees | Civil ID and IBAN are encrypted and shown masked. |
| Leave request | HR → Leave requests → *New* | Working days exclude Friday and Saturday; annual leave is checked against the 30-day balance. |
| Approve / reject | Leave request → buttons | You cannot approve your own request. |

![Employees](screenshots/60-hr-employees.png) ![Leave](screenshots/61-hr-leave.png)

## 8. Data migration (Admin, Accountant, Manager)

1. Data & integration → **Import wizard**; choose what you import and upload a CSV or Excel file.
2. **Map columns**: the wizard suggests a mapping; required fields are marked *.
3. **Validate & cleanse**: rows are *Clean*, *Fixed* (e.g. phone `9123 4567` → `+96891234567`, `MCT` → Muscat) or
   *Rejected* with the reason (missing name, duplicate, negative quantity, invalid date …).
4. **Dry run** shows how many records would be created without saving anything.
5. **Commit** imports valid rows; download the **cleansing report** for the file owner to fix rejected rows.
   Order: suppliers → customers → products → opening stock → opening balances.

![Import mapping](screenshots/70-import-mapping.png) ![Cleansing preview](screenshots/71-import-preview.png)

## 9. Viewer and Power BI users

The Viewer role reads all business data and dashboards but cannot change anything. Power BI reports are
described in `docs/powerbi/dashboard_spec.md`; use the slicers (date, region, warehouse) at the top of each page
and right-click a product or region → *Drill through* for details.

![Power BI executive overview](screenshots/80-powerbi-executive.png)
