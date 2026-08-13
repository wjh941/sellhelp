# Task 1 Implementation Report

## Scope

Implemented Task 1 only: isolated FastAPI API-test infrastructure and transaction request validation.

## Changed Paths

- `backend/app/schemas/all_schemas.py`
- `backend/requirements.txt`
- `backend/pytest.ini`
- `backend/tests/conftest.py`
- `backend/tests/test_transaction_validation.py`
- `.superpowers/sdd/2026-08-13-sellhelp-phase1-hardening/task-1-report.md`

## Baseline

Command:

```powershell
python -m pytest tests/test_transaction_validation.py -q
```

Output: `12 failed, 16 warnings in 0.47s`. Invalid transaction payloads reached route/business handling and returned `400` or `404` instead of FastAPI request-validation `422` responses.

## Final Verification

Commands:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest tests/test_transaction_validation.py -q
$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest -q
```

Output for both commands: `12 passed, 16 warnings`. `pytest.ini` limits collection to `backend/tests`, so `backend/test_api.py` remains a manual HTTP script and was not imported or run. The test fixture uses in-memory SQLite with `StaticPool` and overrides `get_db`; `backend/yingtai.db` is not used.

## Commit

Task 1 implementation commit: `4ae81140fc86ec5492fc99091edbd5fac25a6d91` (`test: add isolated transaction validation coverage`).

## Residual Risk

The test runs retain existing FastAPI TestClient and Pydantic v2 deprecation warnings. They are outside Task 1 scope. Transaction business logic remains intentionally unchanged; this task validates requests before that logic runs.

## Review Corrections

### Changed Paths

- `backend/app/database.py`
- `backend/app/main.py`
- `backend/tests/conftest.py`
- `backend/tests/test_database_isolation.py`
- `frontend/src/views/Purchase.vue`
- `.superpowers/sdd/2026-08-13-sellhelp-phase1-hardening/task-1-report.md`

### Baseline

Command:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest tests/test_database_isolation.py -q
```

Output: `1 failed, 16 warnings in 0.11s`. The configured URL was `sqlite:///.../backend/yingtai.db`, confirming that test imports could bind application initialization to the operator database.

### Final Verification

Commands:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest tests/test_database_isolation.py tests/test_transaction_validation.py -q
$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest -q
```

Output: `13 passed, 18 warnings` for both. The full-suite command also compared SHA-256 hashes before and after pytest: `backend/yingtai.db` was unchanged (`70F36A64721A3DE241DA4E10D08FBDDC5E531885EDC8458FAE9BAFC02F10772E`). The test harness sets `SELLHELP_DATABASE_URL=sqlite://` before importing the app; app table initialization now occurs at startup and uses that configured URL. Purchase creation defaults and client-side validation now require a positive quantity and price, while sales pricing remains unchanged and still permits `0` for server-side derivation.

### Residual Risk

The FastAPI `on_event("startup")` hook introduces an additional framework deprecation warning; migration to FastAPI lifespan handlers is intentionally out of scope. Existing TestClient and Pydantic v2 deprecation warnings remain.
