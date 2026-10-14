# Phase 2 — Accounts and security

Build the accounts app:
- Custom User model (email login), Department FK, phone.
- Create the 7 role groups with model-level permissions via a data migration.
  Restrict UI menus and API endpoints by role.
- TOTP 2FA with django-otp: mandatory for Admin and Accountant, optional for others.
  Include a QR enrolment page.
- django-axes lockout after 5 failed logins; 12+ character password policy;
  30-minute idle session timeout.
- AuditLog model (user, action, model, object_id, changes JSON, IP, timestamp) written
  automatically on create/update/delete of business models through signals or a mixin.
  Read-only audit viewer page for Admin.
- Admin user-management UI.
Tests for permissions, lockout and audit logging. Commit.
