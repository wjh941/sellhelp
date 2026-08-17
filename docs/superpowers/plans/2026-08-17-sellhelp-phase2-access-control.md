# Sellhelp Phase 2 Access Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add role-based authenticated operation, auditable sensitive actions, and matching Vue administration flows while retaining standalone local usage.

**Architecture:** SQLAlchemy models and a forward-only Alembic revision persist identities and audits. One middleware authenticates every API request and defaults unclassified writes to owner-only. Vue uses a small auth store, lazy pages, route metadata, and the same role names.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, PyJWT, Python standard-library PBKDF2, Vue 3, Vue Router, Element Plus, Vite.

## Global Constraints

- Do not alter existing inventory, sales, finance, report, or export business rules.
- Do not add PDF/XLSX export or Playwright tests.
- The Alembic upgrade contains no table or column drop; its downgrade raises before destructive DDL.
- Back up the SQLite file before an operator runs `alembic upgrade head`.
- Preserve `standalone_mode=true` when configuration is absent.

---

### Task 1: Red Authentication And Authorization Tests

**Files:**
- Create: `backend/tests/test_auth_permissions.py`

- [ ] Write tests that prove a missing role cannot create a product or backup a database, a sales clerk can create sales/payments only, a warehouse operator can receive/count stock only, and a logged-out token is rejected.
- [ ] Write tests that verify standalone mode permits legacy business requests and audit logs cannot be updated/deleted by application code.
- [ ] Run: `python -m pytest tests/test_auth_permissions.py -q`
- [ ] Confirm failures are due to missing authentication and authorization implementation.

### Task 2: Safe Auth And Audit Migration

**Files:**
- Create: `backend/alembic/versions/<revision>_auth_and_audit.py`
- Modify: `backend/requirements.txt`
- Modify: `backend/ALEMBIC.md`

- [ ] Add `PyJWT` to requirements.
- [ ] Generate an Alembic revision that creates roles, users, user-role links, and audit logs, inserts three roles and the standalone flag, and disables downgrade.
- [ ] Run the migration against a disposable SQLite file with `python -m alembic -x database_url=sqlite:///C:/Temp/sellhelp-auth-check.db upgrade head`.
- [ ] Run `python -m alembic ... check` and inspect the revision for no `drop_table` or `drop_column` calls.

### Task 3: Backend Security Boundary

**Files:**
- Modify: `backend/app/models/all_models.py`
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/services/audit_service.py`
- Create: `backend/app/security.py`
- Create: `backend/app/routers/auth_router.py`
- Modify: `backend/app/schemas/all_schemas.py`
- Modify: `backend/app/main.py`

- [ ] Implement PBKDF2 hash verification, JWT issue/verify, token-version logout, user/role APIs, and paged audit query.
- [ ] Add centralized route role rules with owner-only defaults for unlisted mutations.
- [ ] Add middleware that recognizes standalone mode, validates bearer tokens, guards every API business route, and records sensitive requests.
- [ ] Add model event guards preventing audit-log update/delete.
- [ ] Run focused backend tests and then the full test suite.

### Task 4: Vue Auth And Administration

**Files:**
- Create: `frontend/src/stores/auth.js`
- Create: `frontend/src/views/Login.vue`
- Create: `frontend/src/views/Accounts.vue`
- Create: `frontend/src/views/AuditLogs.vue`
- Modify: `frontend/src/api/index.js`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/main.js`
- Modify: `frontend/vite.config.js`
- Modify: `frontend/package.json`
- Modify: `frontend/src/styles/main.scss`

- [ ] Add token attachment, auth APIs, a standalone-aware auth bootstrap, and async route guard.
- [ ] Register owner-only Accounts/Audit routes and hide unauthorized navigation/actions.
- [ ] Build the login, account assignment, and paginated audit list flows using existing Element Plus patterns.
- [ ] Configure automatic on-demand Element Plus imports and retain lazy route imports.
- [ ] Run frontend tests and `npm.cmd run build`.

### Task 5: Final Verification And Integration

- [ ] Re-run backend tests, frontend tests, production build, migration check, Python compilation, and `git diff --check`.
- [ ] Inspect the changed UI at desktop and mobile widths without adding Playwright.
- [ ] Commit only Phase 1 hardening and Phase 2 implementation files; leave pre-existing untracked planning documents untouched.
- [ ] Push branch `phase1-hardening` to `origin`.
