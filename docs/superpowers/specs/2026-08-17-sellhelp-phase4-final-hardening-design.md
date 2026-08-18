# SellHelp Phase4 Final Hardening Design

## Scope

Phase4 hardens the completed Phase1-3 inventory application without changing database schema or existing business rules. It fixes Windows PDF Chinese font selection, verifies export authorization, removes production debug residue, reduces frontend delivery cost, adds a small high-value browser suite, and documents operating procedures.

## Decisions

- PDF generation will select a verified Windows CJK font only when ReportLab can load it. The portable `STSong-Light` CID font remains a deterministic fallback for systems without usable Windows fonts.
- `/api/export` remains an owner-only prefix in the global permission middleware. Tests enumerate every concrete export route so a new route cannot silently weaken this policy.
- Playwright uses its own temporary SQLite database and a dedicated backend/frontend port pair. It never writes to `yingtai.db` or the operator's running service.
- Frontend optimization is measurement-led: retain the existing route lazy-loading and chart tree-shaking, remove only unused dependencies or debug code proven unused by the build and test suite.
- No Alembic revision is generated and no database DDL is executed in this phase.

## Acceptance Criteria

1. Chinese PDF data renders through either an installed Windows CJK font or the CID fallback, with a regression test for the selection contract.
2. All export endpoints return 403 for non-owner accounts when `standalone_mode` is disabled.
3. The core role workflow has browser coverage using isolated data: warehouse stock-in, sales order, warehouse return and stock take, owner report download; restricted roles cannot access owner export UI/routes.
4. Backend tests remain at least 125 passing and the frontend production build succeeds.
5. `README-OPERATE.md` is Chinese and covers roles, deployment, SQLite backup, Windows PDF font notes, and release validation.
