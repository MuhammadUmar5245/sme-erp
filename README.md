# SME-ERP + Power BI

Cloud-based modular ERP for SMEs (case company: Al Wadi Trading, Muscat) with Power BI analytics.
This folder is the starter kit. The code is built by Claude Code, phase by phase.

## Prerequisites
- VS Code + the Claude Code extension (or the `claude` CLI)
- Docker Desktop, Git
- Windows + Power BI Desktop (only for Phase 9)

## How to start
1. Unzip and open this folder in VS Code (File > Open Folder).
2. Open a terminal in VS Code and run: `git init && git add . && git commit -m "Starter kit"`
3. Start Claude Code (`claude` in the terminal, or the Claude Code panel).
4. Phase 0 ke liye plan mode on karein, phir type karein:
   `Run the prompt in prompts/00_plan.md`
5. Plan approve karne ke baad, har phase ke liye:
   `Run the prompt in prompts/01_scaffold.md` ... and so on.
6. Har phase ke baad `make test` chalayein aur commit karein, phir next phase.

## Phases
| File | Phase |
|---|---|
| `prompts/00_plan.md` | Phase 0 — Plan (plan mode) |
| `prompts/01_scaffold.md` | Phase 1 — Scaffold |
| `prompts/02_accounts_and_security.md` | Phase 2 — Accounts and security |
| `prompts/03_core_business_modules.md` | Phase 3 — Core business modules |
| `prompts/04_reporting_layer_and_power_bi_service_api.md` | Phase 4 — Reporting layer and Power BI service API |
| `prompts/05_data_migration_and_integrations.md` | Phase 5 — Data migration and integrations |
| `prompts/06_realistic_seed_data.md` | Phase 6 — Realistic seed data |
| `prompts/07_operations_backup_dr_monitoring_and_feas.md` | Phase 7 — Operations: backup, DR, monitoring and feasibility |
| `prompts/08_testing_and_uat.md` | Phase 8 — Testing and UAT |
| `prompts/09_power_bi_kit.md` | Phase 9 — Power BI kit |
| `prompts/10_documentation_for_the_report.md` | Phase 10 — Documentation for the report |

## Folder contents
- `CLAUDE.md` — project context, Claude Code reads it automatically
- `prompts/` — one file per build phase
- `docs/report/project_report.txt` — Chapters 1–6 of the written report (code must match it)
- `docs/claude_code_prompts_full.md` — all prompts in one file
