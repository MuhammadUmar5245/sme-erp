# Phase 10 — Documentation for the report

Generate the following in /docs:
- requirements.md: Functional (FR-01...) and Non-functional (NFR-01...) requirements
  tables, each traced to the report section (e.g. 3.5.1, 2.3.6) and to the
  implementing module and test case.
- diagrams/ (Mermaid): use case diagram, DFD Level 0 and Level 1, ERD, activity diagram
  (order-to-cash), sequence diagram (invoice posting), deployment/architecture diagram
  (users -> HTTPS -> nginx -> Django -> PostgreSQL -> reporting schema -> Power BI).
- user_manual.md per role, with screenshot placeholders named for each page.
- training_plan.md (sessions, audience, duration, materials).
- deployment_azure.md (nearest Middle East region; App Service + Azure Database for PostgreSQL + Blob backup) and
  deployment_aws.md (Middle East region; EC2/ECS + RDS + S3).
- project_signoff.md template (sponsor, deliverables checklist, signatures, date).
- README.md: setup, demo logins per role, screenshots section.
