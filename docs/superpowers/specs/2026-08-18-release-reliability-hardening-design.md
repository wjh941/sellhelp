# Release Reliability Hardening Design

## Scope

This change restores the release verification path and removes confirmed
framework deprecations without changing business rules, API routes, response
fields, database schema, authorization, or frontend workflows.

## Problem Evidence

- The Playwright critical workflow times out while selecting `E2E 测试商品`.
  Element Plus exposes the option as `E2E 测试商品 当前库存 0`, while the shared
  test helper requires an exact accessible name. The test therefore waits for
  a non-existent option and prevents the remaining release scenarios from
  running.
- The backend test suite passes 135 tests but emits 20 warnings. The sources
  are Pydantic v1-style response model configuration, a deprecated `Field`
  keyword, deprecated FastAPI startup/shutdown decorators, and the FastAPI
  re-export of Starlette's deprecated test client.
- The production frontend build completes. Its chart bundle is loaded only by
  lazy routes, and its Sass warnings come from the current build tool chain.
  Neither is changed in this focused release hardening work.

## Design

### E2E option selection

Keep the existing critical workflow and isolated database setup. Change its
shared option helper to select an option whose accessible name begins with the
requested primary label and may include Element Plus secondary text. It must
continue to select the requested option when several menu options are open.

### Pydantic v2 compatibility

Replace each response model's nested `Config` class with the equivalent
Pydantic v2 `ConfigDict(from_attributes=True)` declaration. Replace the
deprecated `Field(comment=...)` metadata with `json_schema_extra` so generated
schema metadata is retained. No request validation, model field, or response
shape changes.

### Application lifecycle

Replace `@app.on_event("startup")` and `@app.on_event("shutdown")` with one
FastAPI lifespan context manager. On startup it initializes the database and
starts the market-sync scheduler unless the existing disable environment
variable is set. On shutdown it shuts down the scheduler, matching present
behavior.

### Test client import

Import `TestClient` directly from Starlette in the backend test fixture. This
preserves the test API while avoiding FastAPI's deprecated re-export.

## Error Handling

- The E2E helper remains strict about the primary option label and does not
  fall back to an arbitrary first result.
- The scheduler's existing startup condition and shutdown behavior are
  preserved; no new error swallowing or retry logic is introduced.

## Acceptance Criteria

1. `npm.cmd run test:e2e` executes all four critical workflow scenarios on its
   isolated SQLite database without timing out.
2. `python -m pytest -q` passes without Pydantic, FastAPI lifecycle, or
   FastAPI TestClient deprecation warnings.
3. Existing API and ORM response behavior remains covered by backend tests.
4. `npm.cmd test` and `npm.cmd run build` remain successful.
5. No migration, schema change, dependency update, or production frontend
   workflow change is included.
