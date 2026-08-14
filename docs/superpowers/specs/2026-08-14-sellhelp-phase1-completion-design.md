# Sellhelp Phase 1 Completion Design

**Date:** 2026-08-14

## Goal

Finish the existing Phase 1 single-store trial release. The system must preserve inventory and receivable integrity, display real operating data, run with one documented configuration, and be reproducible from a clean clone.

## Scope

- Fix the seven failing inventory-integrity tests and retain all existing passing behavior.
- Complete traceable customer returns and strict batch-level stocktakes.
- Make backup file operations server-owned and path-safe.
- Replace Dashboard sample charts with backend aggregates.
- Align runtime ports and add the minimal repository documentation, ignore rules, and CI needed for a clean clone.

## Non-Goals

- No login, user roles, multi-store support, production database migration, Docker, external LLM integration, or full cashbook accounting.
- No rewrite or destructive migration of the existing local `yingtai.db`.
- No new dependencies unless an existing dependency cannot implement the required behavior.

## Inventory And Return Rules

### Purchase cancellation

Deleting a purchase order remains allowed only while every linked batch is fully unconsumed. Before deleting the batch and order, create an immutable `InventoryMovement` with direction `outbound`, reason `purchase_reversal`, the original purchase order number, purchase-order ID, and batch ID. The batch foreign key uses `SET NULL`, so the ledger remains after batch deletion.

### Idempotent sales allocation

`InventoryService.confirm_outbound` first checks whether a `BatchOutbound` exists for the sales item. If it does, it returns without allocating stock or creating a second movement. Otherwise, it retains the existing FIFO allocation and movement behavior.

### Customer return

Customer returns require `related_order_no`. The referenced sales order must exist, belong to the selected customer, and contain the selected product. The requested quantity cannot exceed sold quantity minus prior customer returns for that order and product. The server derives the unit refund from the matching sales item; the client-supplied refund is ignored for this return type.

When the request names a batch, it must belong to the product. When it omits a batch, the server creates a real return batch, associates it with `ReturnOrder.batch_id`, and records an inbound `customer_return` movement. The return decreases the source sales order debt through `ReceivableService`, which updates the customer balance and records a receivable ledger entry in the same transaction.

### Supplier return and stocktake

Supplier returns preserve FIFO allocation when no batch is selected and reject an explicit batch for another product. Stocktake confirmation requires a batch ID, rejects a batch from another product, and accepts only non-negative actual quantity. It creates the stocktake row and a single matching inventory movement only after all per-item validation passes.

## Runtime And Dashboard

### Dashboard metrics

`ReportService` exposes a small read-only aggregate returning seven calendar days of completed-sales amounts and the five products with the highest completed-sales amount for the same period. The Dashboard consumes this endpoint and renders those values. Empty data produces seven zero-valued days and an empty top-product chart; it never generates random values.

### Configuration

The backend continues to default to local SQLite and port `8000`, with database URL and allowed CORS origins read from environment variables. Vite serves on `8080` and proxies `/api` to backend port `8000`. The start script prints and starts the same ports.

### Backup safety

All backup operations use one server-owned `backend/backup` directory. Backup APIs accept no client directory path. Listing only returns managed backup files, while restore, download, and deletion validate an exact base filename with a `.db` suffix and resolve it below the backup directory before filesystem access. Invalid names return HTTP 400.

## Error Handling And Transactions

Router handlers validate all related records before changing state. `HTTPException(400)` is used for invalid business relationships and insufficient eligible stock. A handler commits once after its complete mutation; validation failures occur before a commit, so they leave no inventory movement, receivable ledger, return, or stocktake record.

Inventory mutations remain in `InventoryService`; receivable mutations remain in `ReceivableService`; routers retain request parsing, relationship checks, and response mapping. The frontend remains a thin consumer of `/api` and reports backend error text through its existing Axios interceptor.

## Repository Delivery

- Add `.gitignore` for Python caches, local databases and backups, frontend dependencies, build output, and environment files.
- Add a README with prerequisites, setup, local ports, test/build commands, environment variables, and backup notes.
- Add GitHub Actions to install backend and frontend dependencies, run backend tests, and build the frontend.
- Remove generated directories and the local database from Git tracking without deleting their local copies.

## Verification

- Extend API tests for purchase reversal, idempotent outbound confirmation, explicit return-batch ownership, required customer-return traceability, return quantity cap and receivable adjustment, stocktake validation, backup filename safety, and dashboard aggregates.
- `python -m pytest -q` passes from `backend`.
- `npm.cmd run build` passes from `frontend` outside the execution sandbox restriction that currently prevents the Vite/esbuild child process from reading the workspace path.
- Parse backend Python files and run `git diff --check`.
