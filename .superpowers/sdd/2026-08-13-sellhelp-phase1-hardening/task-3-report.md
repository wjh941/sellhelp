# Task 3 Report: Saleable Inventory and Inventory Ledger

## Changed paths

- `backend/app/models/all_models.py`
- `backend/app/services/inventory_service.py`
- `backend/app/routers/purchase_router.py`
- `backend/app/routers/return_router.py`
- `backend/tests/test_inventory_integrity.py`

No receivable source files or `backend/yingtai.db` were modified. Task 4 and later behavior was not implemented.

## Verification

### Baseline

Command:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest tests/test_inventory_integrity.py -q
```

Result: collection failed as expected because `InventoryMovement` did not yet exist in `app.models.all_models`.

### Final

Focused command:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest tests/test_inventory_integrity.py -q
```

Result: `7 passed, 19 warnings`.

Full backend command:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest -q
```

Result: `35 passed, 19 warnings`.

Warnings are pre-existing FastAPI/httpx and Pydantic deprecations, plus pytest cache write warnings caused by the checkout permissions. Bytecode generation was disabled and no tracked cache files were deleted.

## Implementation summary

- Added date-safe saleable FIFO selection. Expiry today is excluded even when `is_expired` is stale.
- Added defensive positive-quantity checks to inventory service mutation/allocation APIs.
- Added indexed `InventoryMovement` rows with product/batch and optional purchase, sales, return, and stocktake references.
- Recorded movements for purchases, confirmed sales, sale reversals, customer returns, supplier returns, and confirmed stocktake adjustments.
- Kept allocation preview read-only; batch decrements and movement writes occur during confirmation.

## Residual risks

- `Base.metadata.create_all` supports new test databases, but this repository has no migration mechanism for existing deployed SQLite databases; deployment must create the new table through the project’s database upgrade process.
- Existing physical-stock reporting intentionally continues to include expired physical stock; only saleable allocation/return selection is date-safe in Task 3.
- Customer-return traceability and receivable/refund integration remain deferred to Task 4 as requested.
