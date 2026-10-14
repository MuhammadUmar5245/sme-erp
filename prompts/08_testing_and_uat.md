# Phase 8 — Testing and UAT

- Raise test coverage to >= 80% on services; add a coverage report to `make test`.
- Write docs/testing/uat_test_cases.md: at least 40 UAT cases (ID, module, role,
  preconditions, steps, expected result, actual result, status) covering every module,
  security (RBAC, 2FA, lockout), import/cleansing, reports and backup/restore.
- Write docs/testing/test_summary.md with the unit/integration results table.
- Optional: a locustfile.py load test for 50 concurrent users, with results recorded.
