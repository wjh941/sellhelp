# Task 2 Report: Receivables Service and Payment Correctness

## Scope

Implemented Task 2 only. Task 3 inventory, Task 4 returns, runtime configuration, and frontend changes were not touched.

## Changed Paths

- `backend/app/models/all_models.py`
- `backend/app/services/receivable_service.py`
- `backend/app/routers/sales_router.py`
- `backend/app/routers/finance_router.py`
- `backend/app/routers/customer_router.py`
- `backend/tests/conftest.py`
- `backend/tests/test_receivables.py`

## Baseline

Command:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest tests/test_receivables.py -q
```

After correcting a pytest collection-only parameter-name error in the new test file, the pre-implementation baseline was `6 failed, 18 warnings in 0.52s`.

Observed failures were the expected missing behavior: cash and complete-payment transitions left customer debt unchanged, the ledger table did not exist, and customer/finance/batch repayment paths did not consistently allocate oldest-first.

## Implementation

`ReceivableService.apply_order_balance_change` computes `new_debt - old_debt` once, updates the customer aggregate once, and writes a signed ledger row linked to the customer and sales order. `apply_payment` rejects overpayment, allocates oldest outstanding orders first, updates paid/debt/payment status, updates the customer aggregate once, and writes one negative ledger row per allocation.

`ReceivableLedger` is included in `Base.metadata.create_all`, so fresh test databases and existing local SQLite databases gain the table without destructive changes.

All direct `current_debt` mutations in sales, finance, and customer payment routes were removed; only `ReceivableService` writes the aggregate.

## Final Verification

Commands run with `PYTHONDONTWRITEBYTECODE=1`:

```powershell
python -m pytest tests/test_receivables.py -q
```

Result: `8 passed, 18 warnings in 0.48s`.

```powershell
python -m pytest -q
```

Result: `21 passed, 18 warnings in 0.77s`.

The warnings are existing FastAPI/httpx and Pydantic deprecations outside Task 2 scope.

## Commits

- Implementation: `b574b7d` (`fix: centralize receivable balance transitions`)
- Report: separate documentation commit recorded after this report update

## Residual Risks

- The system still uses floating-point monetary columns and values, consistent with the existing schema.
- No migration framework exists; `create_all` adds the new ledger table but does not reconcile historical customer aggregates or backfill historical ledger rows.
- Existing framework deprecation warnings remain outside this task.
