# Sellhelp Phase 1 Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a testable, single-store trial release that keeps inventory and receivables correct and can be built from a clean clone.

**Architecture:** FastAPI routers retain HTTP concerns while `ReceivableService` and `InventoryService` own balance and stock mutations. Tests use FastAPI dependency overrides with an in-memory SQLite database. Vite remains the frontend build tool and reads one backend origin through its `/api` proxy.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2, Pydantic 2, pytest, Vue 3, Vite 5, Element Plus, ECharts.

## Global Constraints

- Keep the existing frontend/backend structure and Chinese business terms.
- New and changed business behavior requires a test written and observed failing before implementation.
- Never mutate the operator database during tests.
- Use backend port `8000` and frontend port `8080` in source, test tooling, and startup documentation.
- Do not add authentication or a production database migration in Phase 1.

---

### Task 1: Isolated API Test Harness and Input Contracts

**Files:**
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_transaction_validation.py`
- Modify: `backend/app/schemas/all_schemas.py`
- Modify: `backend/requirements.txt`

**Interfaces:**
- Produces a `client` pytest fixture backed by an in-memory SQLite database.
- Produces constrained Pydantic request models that reject non-positive transaction quantities and invalid enum-like values.

- [ ] Write failing API tests for negative purchase/sale/return quantities, empty item lists, invalid return types, and invalid payment values.
- [ ] Run `python -m pytest tests/test_transaction_validation.py -q` and confirm validation failures are not currently rejected.
- [ ] Add `Decimal`, `Annotated`, `Field`, and model validators to request schemas; add pytest and compatible httpx test dependencies.
- [ ] Re-run the focused test file and then `python -m pytest -q`.
- [ ] Commit with message `test: add isolated transaction validation coverage`.

### Task 2: Receivables Service and Payment Correctness

**Files:**
- Create: `backend/app/services/receivable_service.py`
- Create: `backend/tests/test_receivables.py`
- Modify: `backend/app/models/all_models.py`
- Modify: `backend/app/routers/sales_router.py`
- Modify: `backend/app/routers/finance_router.py`
- Modify: `backend/app/routers/customer_router.py`

**Interfaces:**
- `ReceivableService.apply_order_balance_change(order, old_debt, reason, reference_no)` applies exactly one customer balance delta and writes a `ReceivableLedger` row.
- `ReceivableService.apply_payment(customer, amount, allocations, remark)` applies payments oldest-first and persists negative receivable movements.

- [ ] Write failing tests that show cash settlement and complete payment reduce customer debt exactly once, and partial payment changes only the remaining balance.
- [ ] Run `python -m pytest tests/test_receivables.py -q` and confirm current behavior fails.
- [ ] Add the ledger model and centralized receivable service; replace direct customer debt mutations in sales, finance, and customer payment routes.
- [ ] Run focused receivable tests and the full backend suite.
- [ ] Commit with message `fix: centralize receivable balance transitions`.

### Task 3: Saleable Inventory and Inventory Ledger

**Files:**
- Modify: `backend/app/models/all_models.py`
- Modify: `backend/app/services/inventory_service.py`
- Modify: `backend/app/routers/purchase_router.py`
- Modify: `backend/app/routers/sales_router.py`
- Modify: `backend/app/routers/return_router.py`
- Create: `backend/tests/test_inventory_integrity.py`

**Interfaces:**
- `InventoryService.find_fifo_batches(product_id, quantity)` returns only non-expired batches and raises a value error if saleable stock is insufficient.
- `InventoryService.record_movement(...)` persists `InventoryMovement` rows for purchase, sale, reversal, return, and stocktake changes.

- [ ] Write failing tests for expired-batch allocation rejection and inventory ledger entries for purchase and sale.
- [ ] Run `python -m pytest tests/test_inventory_integrity.py -q` and confirm expired stock is currently allocated.
- [ ] Separate physical batches from saleable batches, record movements, and integrate them into purchase, outbound, reversals, returns, and stocktakes.
- [ ] Run focused inventory tests and the full backend suite.
- [ ] Commit with message `fix: prevent expired stock sales and record inventory movements`.

### Task 4: Customer Return Integrity

**Files:**
- Modify: `backend/app/routers/return_router.py`
- Modify: `backend/app/services/receivable_service.py`
- Create: `backend/tests/test_customer_returns.py`

**Interfaces:**
- Customer returns require `related_order_no` and match a sold product.
- The returned quantity is capped by sold quantity minus previously recorded customer returns for the same sales order and product.
- Return value is derived from the originating sales item, not accepted from client input.

- [ ] Write failing tests for missing/unknown source orders, product mismatch, over-return, and a valid credit-sale return reducing receivables.
- [ ] Run `python -m pytest tests/test_customer_returns.py -q` and confirm the invalid requests are accepted.
- [ ] Implement relationship checks, derived refund calculation, stock return movement, sales-order debt adjustment, and receivable ledger entry.
- [ ] Run focused return tests and the full backend suite.
- [ ] Commit with message `fix: enforce customer return traceability`.

### Task 5: Runtime Configuration, Backup Safety, and Dashboard Data

**Files:**
- Modify: `backend/app/database.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/routers/system_router.py`
- Modify: `backend/app/routers/report_router.py`
- Modify: `backend/app/services/report_service.py`
- Modify: `frontend/vite.config.js`
- Modify: `frontend/src/views/Dashboard.vue`
- Modify: `start.bat`
- Modify: `backend/test_api.py`
- Create: `backend/tests/test_system_safety.py`

**Interfaces:**
- Database URL, allowed origins, and ports have environment-backed defaults.
- Backup route accepts no directory path and validates backup filenames against the server-owned directory.
- Dashboard consumes a backend endpoint returning seven daily totals and five real top products.

- [ ] Write failing tests for unsafe backup filenames and dashboard aggregation values.
- [ ] Run `python -m pytest tests/test_system_safety.py -q`.
- [ ] Implement constrained configuration, safe backup resolution, aligned ports, backend dashboard metrics, and frontend chart rendering from API data.
- [ ] Run backend tests and `npm.cmd run build`.
- [ ] Commit with message `fix: align runtime configuration and dashboard data`.

### Task 6: Clean Repository, Documentation, and Continuous Integration

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `.github/workflows/ci.yml`
- Delete from index: `frontend/node_modules/**`, `backend/**/__pycache__/**`, `backend/yingtai.db`

**Interfaces:**
- A clean clone installs dependencies using `backend/requirements.txt` and `frontend/package-lock.json`.
- CI runs backend tests and frontend build on pushes and pull requests.

- [ ] Add a failing cleanliness check that asserts generated paths are ignored.
- [ ] Add `.gitignore`, README setup and backup guidance, and a GitHub Actions workflow.
- [ ] Remove generated dependencies, caches, and local database from Git tracking without deleting local working copies.
- [ ] Run `git status --short`, backend tests, and frontend production build.
- [ ] Commit with message `chore: make sellhelp reproducible from a clean clone`.

## Final Verification

- [ ] Run `python -m pytest -q` from `backend`.
- [ ] Run `npm.cmd run build` from `frontend`.
- [ ] Parse all backend Python source with `ast.parse`.
- [ ] Inspect `git diff main...HEAD --check` and `git status --short`.
- [ ] Push branch `phase1-hardening` to the configured `origin` remote.
