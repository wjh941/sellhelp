# Sellhelp Phase 2 Access Control Design

## Goal

Add accountable multi-user operation without changing inventory, sales, finance, or reporting rules. The default `standalone_mode=true` preserves the existing single-machine workflow.

## Data And Migration

The next Alembic revision follows `d8f13722a89d` and creates `roles`, `users`, `user_roles`, and `audit_logs`. It inserts the immutable built-in role codes `owner`, `warehouse_operator`, and `sales_clerk`, and adds `standalone_mode=true` only when the system configuration is absent. Its upgrade contains only `create_table`, indexes, and non-destructive inserts; its downgrade is blocked.

An operator with a populated database must stop the backend, copy the SQLite file, confirm the Phase 1 revision is stamped, then run `alembic upgrade head`. A brand-new empty database can run `upgrade head` directly.

## Authentication And Permissions

Passwords use `hashlib.pbkdf2_hmac` with a per-user random salt. JWTs use `PyJWT`, carry a user id and authentication version, and require `SELLHELP_JWT_SECRET` when standalone mode is disabled. Logout increments that authentication version, invalidating active tokens for that account.

The global middleware owns authorization. It permits only health and login before authentication; in standalone mode it supplies a virtual owner. In authenticated mode, every `/api` route is covered: read-only business views are available to the three roles unless explicitly sensitive, unclassified mutations require `owner`, and the allow-list grants only warehouse stock workflows and sales order/payment workflows to the corresponding operational role.

| Role | Allowed mutations |
| --- | --- |
| `owner` | All operations, including users, configuration, backups/restores, pricing, and document deletion |
| `warehouse_operator` | Purchase stock-in, permitted stock-out/returns, and stock counting |
| `sales_clerk` | Create sales orders and record payments |

Backups/restores, configuration, accounts, audit logs, price changes, and every document delete are explicitly owner-only. The middleware audits successful and denied mutating requests with the authenticated user, client IP, operation, path, and status. Audit records have no mutation/deletion API and SQLAlchemy listeners reject application-level updates and deletes.

## Frontend

Vue keeps its existing operational blue/orange light/dark visual system. A small reactive auth store initializes from `/api/auth/me`; the global route guard redirects unauthenticated users to `/login` and applies route-level role metadata. Sidebar items and account controls use the same role contract.

New lazy-loaded views are Login, Accounts, and Audit Logs. Accounts and audit logs are owner-only. Element Plus imports move to `unplugin-vue-components` so components are compiled on demand rather than registered globally. Shared CSS refines card headers, filters, tables, forms, buttons, focus states, and motion without changing business flow.

## Non-Goals

This phase does not add PDF/XLSX export, Playwright E2E coverage, changed business calculations, or a default production password.
