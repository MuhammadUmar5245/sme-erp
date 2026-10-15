# SME-ERP — Requirements and Traceability

Each requirement is traced to the written report section that motivates it, the module that
implements it, and the automated tests / UAT cases that verify it.

## Functional requirements

| ID | Requirement | Report § | Module | Tests |
|---|---|---|---|---|
| FR-01 | Users log in with e-mail and password; log out explicitly | 4.6 | accounts | `accounts/tests/test_security.py` |
| FR-02 | Seven roles (Admin, Manager, Accountant, SalesOfficer, Storekeeper, HROfficer, Viewer) restrict menus, pages and API endpoints | 4.6, 5.1.1 | accounts (`roles.py`) | `accounts/tests/test_permissions.py` |
| FR-03 | TOTP two-factor authentication with QR enrolment; mandatory for Admin and Accountant | 2.3.6 | accounts | `test_security.py::test_enrolment_*`, `test_user_with_device_must_verify_after_password` |
| FR-04 | Every create/update/delete on business data and every login is written to an immutable audit log, viewable by Admin | 4.6, 2.3.6 | accounts (`audit.py`) | `accounts/tests/test_audit.py` |
| FR-05 | Admin manages users: create, edit, assign roles, deactivate, reset 2FA, unlock | 5.1.1 | accounts | `accounts/tests/test_user_management.py` |

## Non-functional requirements

| ID | Requirement | Report § | Implementation | Tests |
|---|---|---|---|---|
| NFR-01 | Web UI usable on desktop, tablet and mobile | 2.3.5, 2.3.8, 4.4.1 | Bootstrap 5 responsive layout, off-canvas sidebar | UAT |
| NFR-02 | All traffic encrypted in transit (HTTPS, HTTP→HTTPS redirect, TLS to PostgreSQL) | 4.4.4, 4.6 | nginx TLS 1.2/1.3, HSTS; PostgreSQL `ssl=on` | UAT |
| NFR-03 | Account lockout after 5 failed logins (30 min) | 2.3.6 | django-axes | `test_security.py::test_account_locked_after_five_failed_logins` |
| NFR-04 | Passwords ≥ 12 characters; sessions expire after 30 minutes idle | 2.3.6 | Django password validators, session settings | `test_password_policy_requires_12_characters`, `test_session_idle_timeout_is_30_minutes` |
| NFR-05 | Health endpoint reports application and database status | 3.5.4, 5.2.3 | `/health/` | `core/tests/test_smoke.py` |
| NFR-06 | RESTful service layer with OpenAPI documentation | 4.4.1 | DRF `/api/v1/`, `/api/docs/` | API tests per module |
