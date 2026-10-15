# Project Sign-Off

Report reference: §3.7 (Project Sign-Off Section). This form records that the project sponsor and the key
stakeholders accept that the objectives have been achieved before moving to the next stage (go-live).

| | |
|---|---|
| **Project** | Cloud-based modular ERP with Power BI analytics |
| **Organisation** | Al Wadi Trading & Distribution LLC, Muscat, Sultanate of Oman |
| **Project sponsor** | ______________________ (General Manager) |
| **Project manager** | ______________________ |
| **Version / release** | 1.0 (git tag: ________) |
| **Sign-off stage** | ☐ Design ☐ UAT completion ☐ Go-live ☐ Post-implementation review |
| **Date** | ____ / ____ / 20____ |

## 1. Objectives (report §3.2)

| Objective | Evidence | Accepted |
|---|---|---|
| Understand SME problems and how the ERP addresses them | Report Ch. 1–3, `docs/requirements.md` | ☐ |
| Assess costs and benefits (qualitative and quantitative) | Feasibility calculator (ROI, NPV, IRR, payback, TCO) and PDF | ☐ |
| Map SME needs to ERP features | Traceability matrix `docs/requirements.md` (FR-01…FR-35, NFR-01…NFR-18) | ☐ |
| Address adoption challenges (cost, resistance, skills) | `docs/training_plan.md`, user manual, cloud subscription model | ☐ |
| Provide an implementation model | Deployment guides, data migration wizard, DR plan | ☐ |

## 2. Deliverables checklist

| # | Deliverable | Location | Delivered | Accepted |
|---|---|---|---|---|
| 1 | Modular cloud ERP (accounts, inventory, purchasing, sales, CRM, finance, HR, reports, integrations, monitoring, feasibility) | source code | ☐ | ☐ |
| 2 | RESTful service layer with OpenAPI documentation | `/api/v1/`, `/api/docs/` | ☐ | ☐ |
| 3 | Security: RBAC (7 roles), 2FA, lockout, audit log, encryption in transit and at rest | accounts, nginx, PostgreSQL SSL | ☐ | ☐ |
| 4 | Responsive web UI (desktop, tablet, mobile) | application | ☐ | ☐ |
| 5 | Reporting schema, Power BI API and Power BI kit (guide, M, DAX, model, dashboard spec, theme) | `docs/powerbi/` | ☐ | ☐ |
| 6 | Data migration with cleansing and cleansing reports | import wizard, `sample_data/legacy/` | ☐ | ☐ |
| 7 | Backup and disaster recovery (RPO 24 h, RTO 4 h) with tested restore | `docs/disaster_recovery.md` | ☐ | ☐ |
| 8 | Performance monitoring (in-app and Power BI) | monitoring page | ☐ | ☐ |
| 9 | Testing: unit/integration (≥ 80 % coverage), UAT cases, load test | `docs/testing/` | ☐ | ☐ |
| 10 | Requirements and models (use case, DFD, ERD, activity, sequence, deployment) | `docs/requirements.md`, `docs/diagrams/` | ☐ | ☐ |
| 11 | User manual and training plan | `docs/user_manual.md`, `docs/training_plan.md` | ☐ | ☐ |
| 12 | Cloud deployment guides (Azure UAE North, AWS me-central-1) | `docs/deployment_*.md` | ☐ | ☐ |

## 3. Test results

| Item | Result | Comment |
|---|---|---|
| Automated tests (`make test`) | ____ passed / ____ failed | |
| Business-logic coverage | ______ % (target ≥ 80 %) | |
| UAT cases executed by users | ____ / 49 passed | Open issues: |
| Restore test | ☐ Pass ☐ Fail — date ________ | |
| Power BI reconciliation (revenue YTD = ERP KPI) | ☐ Pass ☐ Fail | |

## 4. Open issues and conditions

| # | Issue / condition | Owner | Due date |
|---|---|---|---|
| 1 | | | |
| 2 | | | |

## 5. Approval

By signing, the signatories confirm that the deliverables above meet the agreed requirements, subject to the
conditions listed in section 4.

| Role | Name | Signature | Date |
|---|---|---|---|
| Project sponsor (General Manager) | | | |
| Finance Manager | | | |
| Operations Manager | | | |
| IT & ERP Administrator | | | |
| Project manager / developer | | | |
| Academic supervisor (if applicable) | | | |
