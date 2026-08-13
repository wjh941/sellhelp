# Task 2 Report: Receivables Service and Payment Correctness

## Scope

Implemented Task 2 corrective fixes only. Inventory, returns, runtime configuration, and frontend files were not touched.

## Changed Paths

- `backend/app/models/all_models.py`
- `backend/app/services/receivable_service.py`
- `backend/app/routers/sales_router.py`
- `backend/app/routers/finance_router.py`
- `backend/app/routers/customer_router.py`
- `backend/tests/test_receivables.py`

## Baseline

Command:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest tests/test_receivables.py -q
```

The correction regression baseline was:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest tests/test_receivables.py -q -k 'customer_delete_rejects or inconsistent or credit_limit'
```

Result: `4 failed, 8 deselected, 20 warnings in 1.44s`.

Observed failures were the verified review findings: customer deletion attempted to null the non-nullable ledger customer FK, inconsistent customer/order aggregates were accepted, payment mutation behavior was not atomic on rejection, and changing an order to credit bypassed the customer credit limit.

## Implementation

`ReceivableService.apply_order_balance_change` computes `new_debt - old_debt` once, updates the customer aggregate once, and writes a signed ledger row linked to the customer and sales order. `apply_payment` rejects overpayment, allocates oldest outstanding orders first, updates paid/debt/payment status, updates the customer aggregate once, and writes one negative ledger row per allocation.

The correction adds a block-until-reconciled invariant check comparing `Customer.current_debt` with outstanding `SalesOrder.debt_amount`. Order transitions account for the old order debt before accepting the new debt, and payment validation runs before ORM mutation. Customer deletion now rejects any receivable ledger history with HTTP 400. Payment changes enforce the resulting customer credit limit before changing the order. Customer/finance payment error handlers roll back, and batch repayment uses a savepoint per item so caught failures cannot be committed later.

`ReceivableLedger` is included in `Base.metadata.create_all`, so fresh test databases and existing local SQLite databases gain the table without destructive changes.

All direct `current_debt` mutations in sales, finance, and customer payment routes were removed; only `ReceivableService` writes the aggregate.

## Final Verification

Commands run with `PYTHONDONTWRITEBYTECODE=1`:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest tests/test_receivables.py tests/test_transaction_validation.py -q
```

Result: `25 passed, 19 warnings in 0.95s`.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest -q
```

Result: `26 passed, 19 warnings in 0.94s`.

The warnings are existing FastAPI/httpx and Pydantic deprecations outside Task 2 scope.

## Commits

- Implementation: `b574b7d` (`fix: centralize receivable balance transitions`)
- Correction: `3a0e5a8` (`fix: harden receivable invariants and payment transitions`)
- Report: documentation commit recorded after this report update

## Residual Risks

- The system still uses floating-point monetary columns and values, consistent with the existing schema.
- No migration framework exists; `create_all` adds the new ledger table but does not reconcile historical customer aggregates or backfill historical ledger rows.
- Existing inconsistent customer/order aggregates remain blocked until reconciled; this correction intentionally adds no backfill migration.
- Existing framework deprecation warnings remain outside this task.
