# Phase 1 — Scaffold

Implement the project skeleton per docs/plan.md:
- docker-compose.yml with web, db and nginx. nginx serves HTTPS with a self-signed cert
  (script in scripts/gen_cert.sh) and redirects HTTP to HTTPS.
- Django project `config` with split settings (base/dev/prod) reading from .env; .env.example.
- Makefile with the commands listed in CLAUDE.md.
- Base responsive layout: sidebar navigation per module (collapses on mobile), top bar
  with user menu, login/logout pages, and a placeholder dashboard.
- Health check endpoint /health/ returning DB status.
- pytest configured; one smoke test.
Verify that `make up` and `make test` pass, then commit.
