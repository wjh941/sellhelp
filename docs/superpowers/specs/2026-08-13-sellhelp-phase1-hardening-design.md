# Sellhelp Phase 1 Hardening Design

**Date:** 2026-08-13

## Goal

Make the existing single-store trading system safe for real trial data by preserving receivables and inventory integrity, rejecting invalid transactions, preventing sales of expired stock, and making the application reproducible to run and test.

## Scope

Phase 1 covers P0 and the first operational parts of P1 from the audit:

- Create a repeatable pytest API test harness with isolated SQLite databases.
- Validate positive quantities and amounts, legal payment and return types, non-empty item lists, and valid batch dates.
- Centralize receivable transitions so creating, changing, completing, deleting, and returning sales orders keep `SalesOrder.debt_amount` and `Customer.current_debt` synchronized.
- Add immutable inventory and receivable ledgers for every new business movement. Existing rows remain readable; new changes are ledger-backed.
- Exclude expired batches from outbound allocation while retaining them in expiry reporting and physical-stock views.
- Require customer returns to reference a matching sales order and cap the return quantity at the unreturned sold quantity.
- Remove public path selection from backup operations, restrict backup filenames to a safe default directory, and make CORS configurable for local deployment.
- Align API, frontend, test, and start-script ports at frontend 8080 / backend 8000.
- Replace dashboard sample charts with backend data aggregations.
- Add `.gitignore`, README, CI, and remove tracked local dependencies, caches, and database artifacts.

## Non-Goals

- Multi-user roles, login, password management, PostgreSQL, Docker deployment, full payment/cashbook accounting, and external LLM integration are Phase 2 or later.
- No destructive migration of the existing `yingtai.db` is performed in Phase 1. New ledger tables are created through the schema bootstrap and the README documents a fresh-data trial workflow.

## Architecture

Business mutations remain in FastAPI router modules but delegate shared accounting and stock effects to services. `ReceivableService` computes the delta between an order's old and new receivable amount, adjusts the customer balance exactly once, and persists a `ReceivableLedger` row. `InventoryService` creates `InventoryMovement` records and separates saleable batches from total physical batches.

API validation is expressed through Pydantic schema constraints and router-level relationship checks. API tests run against a per-test in-memory SQLite database with FastAPI dependency overrides, so no test reads or mutates an operator database.

## Data Rules

- Currency values use two-decimal `Decimal` calculations at service boundaries before persistence to existing numeric fields.
- Quantities must be greater than zero for purchase, sale, and return requests.
- A customer return references an existing sales order containing the product. The total returned quantity for the order/product combination cannot exceed the sold quantity.
- Expired batches never satisfy an outbound allocation. They remain available in expiry reports and physical inventory records.
- A receivable adjustment always uses `new_order_debt - old_order_debt`; no handler manually increments and decrements customer debt outside `ReceivableService`.
- Backups always use the server-owned `backend/backup` directory; client parameters cannot select paths.

## Verification

- Pytest covers validation, payment changes, complete payment, expired-stock rejection, return caps, and safe backup filename handling.
- `python -m pytest` passes from `backend`.
- `npm.cmd run build` passes from `frontend`.
- Python source parses cleanly.
- Git status contains only intended source, documentation, configuration, and removal changes before commit.
