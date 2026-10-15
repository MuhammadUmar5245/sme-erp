# Training Plan

Report reference: §5.1.5 (User Training Plan), §2.5.2 (user readiness), §1.3.2 / §6.1 (resistance to change).

**Approach.** Role-based, hands-on sessions in a training copy of the system loaded with the Al Wadi demo data
(`make seed`), so trainees practise on realistic customers, products and invoices without affecting live data.
Sessions are in English with Arabic support from a bilingual super-user. Each department nominates a
**super-user** who attends an extra session and becomes the first line of support.

## Schedule (2 weeks before go-live)

| # | Session | Audience | Duration | Content | Materials |
|---|---|---|---|---|---|
| 1 | ERP overview and logging in | All 25 system users | 1 h | Why the ERP, navigation, desktop vs phone, 2FA set-up, passwords, help desk | User manual §1, demo system, authenticator app |
| 2 | Sales and CRM | Sales officers (6), customer service (4) | 3 h | Customers and Customer 360, sales orders, invoices with VAT, payments, credit notes, interactions, feedback | User manual §5, UAT-19–26 as exercises |
| 3 | Stock and purchasing | Storekeepers (4), procurement (2), supervisors (2) | 3 h | Stock levels, transfers, adjustments, receiving goods, low-stock alerts, tablet use in the warehouse | User manual §6, UAT-12–17 |
| 4 | Finance | Accountants (3), finance manager | 4 h | Supplier bills and payments, receipts, journals, expenses, VAT return, aging, trial balance, P&L, opening balances | User manual §4, UAT-27–30 |
| 5 | HR | HR officer, managers | 1.5 h | Employees, leave requests, approvals | User manual §7, UAT-31–33 |
| 6 | Management dashboards and Power BI | GM, managers (4), finance manager | 2 h | In-app dashboard, report builder, feasibility calculator, reading the Power BI pages, slicers and drill-through | `docs/powerbi/dashboard_spec.md`, Power BI report |
| 7 | Data migration workshop | Admin, finance manager, super-users | 2 h | Import wizard, cleansing rules, reading the cleansing report, fixing legacy files | `sample_data/legacy/`, User manual §8 |
| 8 | Administration and security | IT & ERP administrator | 3 h | Users and roles, 2FA reset, lockouts, audit log, monitoring, backup/restore drill, Power BI gateway | `docs/disaster_recovery.md`, `docs/powerbi/connection_guide.md` |
| 9 | Super-user session | One super-user per department (6) | 2 h | Common problems, how to answer colleagues, raising tickets | Help & support page, FAQ |

## Materials

- `docs/user_manual.md` (per role, with screenshots), printed quick-reference card per role (one page).
- Short screen recordings (3–5 min) per task, stored on the company SharePoint.
- Exercise sheets based on the UAT cases in `docs/testing/uat_test_cases.md`.
- In-app **Help & support** page (help-desk contacts, response targets, feedback form).

## Evaluation (report §5.1.4)

1. Short quiz at the end of each session (pass mark 80 %; repeat session if lower).
2. Users rate the system in **Help → Help & support** in week 1 and week 4 after go-live; the Admin reviews
   *Administration → User evaluation* (average per area, open problems) in the weekly ERP meeting.
3. Target: average rating ≥ 4.0/5 and no open "problem" older than one week by the end of month 1.
4. Refresher sessions for areas rated below 3.5, and for new staff during onboarding.

## Support after go-live (report §5.1.5, §5.2.1)

| Period | Support |
|---|---|
| Weeks 1–2 (hypercare) | Super-users on the floor at Muscat and Sohar; ERP administrator on call 08:00–20:00 |
| Weeks 3–8 | Help desk (e-mail, phone, WhatsApp) with response targets: critical 1 h, high 4 h, normal 1 working day |
| Ongoing | Monthly user meeting, quarterly refresher, release notes for every update |
