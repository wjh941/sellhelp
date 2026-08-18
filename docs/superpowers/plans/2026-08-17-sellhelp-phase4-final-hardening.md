# SellHelp Phase4 Final Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the completed inventory system safer to release by repairing Windows CJK PDF output, proving owner-only export access, reducing production debug/bundle residue, and adding critical-path browser coverage.

**Architecture:** Keep authorization in `PermissionMiddleware` and document/export behavior in existing router and service boundaries. E2E launches FastAPI and Vite against an isolated SQLite file, seeds only E2E fixtures through public APIs, and validates the actual Vue interface. No models or migrations change.

**Tech Stack:** FastAPI, SQLAlchemy/SQLite, ReportLab, Vue 3, Vite, Element Plus, Playwright.

## Global Constraints

- No database schema change; do not generate or apply an Alembic migration.
- Preserve Phase1-3 business rules, existing light/dark dashboard presentation, and existing user interactions.
- `/api/export/*` is owner-only when `standalone_mode=false`.
- E2E uses a dedicated temporary SQLite database and must not point at `yingtai.db`.
- Do not add PDF/XLSX business features beyond Phase3.

---

### Task 1: CJK PDF font selection and export authorization

**Files:**
- Modify: `backend/app/services/document_export_service.py`
- Modify: `backend/tests/test_export_files.py`
- Modify: `backend/tests/test_auth_permissions.py`

**Interfaces:**
- Consumes: `_pdf_font_name() -> str`, `allowed_roles(method: str, path: str) -> set[str>`.
- Produces: PDFs that use a usable Windows CJK font or `STSong-Light`, and route coverage for every `/api/export` endpoint.

- [ ] **Step 1: Write failing regression tests**

```python
def test_pdf_font_falls_back_to_cjk_cid_font_when_windows_font_is_unavailable(monkeypatch):
    monkeypatch.setattr(export_service, "WINDOWS_CJK_FONT_CANDIDATES", ())
    export_service._PDF_FONT_NAME = None
    assert export_service._pdf_font_name() == "STSong-Light"
```

Add a parametrized test that sends each export path using a sales-clerk or warehouse token and asserts `403`.

- [ ] **Step 2: Run the selected tests and observe the expected failure**

Run: `python -m pytest backend/tests/test_export_files.py backend/tests/test_auth_permissions.py -q`

Expected: the newly introduced font-selection assertion fails before the fallback contract is explicit.

- [ ] **Step 3: Implement the smallest portable font resolver**

```python
WINDOWS_CJK_FONT_CANDIDATES = ("simhei.ttf", "msyh.ttc", "simsun.ttc")

def _pdf_font_name() -> str:
    for path in _windows_cjk_font_paths():
        if _register_windows_cjk_font(path):
            return _PDF_FONT_NAME
    return _register_cid_fallback()
```

Keep a named CID fallback and avoid silently selecting a non-CJK default font.

- [ ] **Step 4: Re-run the focused tests**

Run: `python -m pytest backend/tests/test_export_files.py backend/tests/test_auth_permissions.py -q`

Expected: PASS.

### Task 2: Production-source cleanup and frontend size reduction

**Files:**
- Modify: backend production Python files only where dead debug/commented code is found.
- Modify: `frontend/src/**/*.js`, `frontend/src/**/*.vue`, and `frontend/package.json` only for proven unused debug code/dependencies.
- Modify: `frontend/vite.config.js` to make the E2E proxy target configurable without changing the default developer port.

**Interfaces:**
- Consumes: existing npm build scripts and Vite proxy behavior.
- Produces: a behaviorally identical production bundle with no source `console.log` / debugger statements.

- [ ] **Step 1: Establish a build baseline**

Run: `npm.cmd run build` from `frontend` and record the emitted asset sizes.

- [ ] **Step 2: Write a source policy test or extend the static suite**

```js
test('production source has no console logging or debugger statements', () => {
  assert.equal(sourceFiles.some(hasForbiddenDebugStatement), false)
})
```

- [ ] **Step 3: Remove only confirmed debug/dead code**

Use `rg` to find `console.log`, `debugger`, and legacy commented-out executable code. Keep explanatory comments that document non-obvious safety behavior.

- [ ] **Step 4: Run frontend tests and build again**

Run: `npm.cmd run test` and `npm.cmd run build`.

Expected: tests pass and emitted chunks do not grow.

### Task 3: Critical-path Playwright suite

**Files:**
- Modify: `frontend/package.json`, `frontend/package-lock.json`, `frontend/vite.config.js`
- Create: `frontend/playwright.config.mjs`
- Create: `frontend/tests/e2e/*.spec.mjs`
- Create: `frontend/tests/e2e/global-setup.mjs`

**Interfaces:**
- Consumes: FastAPI public APIs for safe E2E seed data, login page, role-driven menu, and export controls.
- Produces: `npm.cmd run test:e2e` using a dedicated `SELLHELP_DATABASE_URL` temporary file.

- [ ] **Step 1: Add a failing smoke specification**

```js
test('warehouse, sales clerk, and owner complete their critical permitted steps', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '登录系统' })).toBeVisible()
})
```

- [ ] **Step 2: Install the test runner and Chromium**

Run: `npm.cmd install --save-dev @playwright/test` then `npx playwright install chromium`.

- [ ] **Step 3: Configure isolated web servers and deterministic seed data**

Use a temporary database file and Vite proxy target for the test process; set `SELLHELP_DISABLE_MARKET_SYNC_SCHEDULER=1`, provision the three accounts before disabling standalone mode, and never target `yingtai.db`.

- [ ] **Step 4: Implement focused scenarios**

Cover warehouse stock-in, sales-clerk sale, warehouse return/stock count, owner download, plus forbidden menu/page/export checks for non-owner accounts.

- [ ] **Step 5: Run the browser suite**

Run: `npm.cmd run test:e2e`.

Expected: all selected Chromium tests pass.

### Task 4: Chinese operating documentation and release verification

**Files:**
- Create: `README-OPERATE.md`

**Interfaces:**
- Consumes: documented owner, warehouse operator, sales clerk permissions and the SQLite deployment layout.
- Produces: a Chinese operational guide and manual release checklist.

- [ ] **Step 1: Write the guide**

Document installation/startup commands, each role's permitted and forbidden actions, a timestamped SQLite backup copy procedure, recovery cautions, Windows Chinese font behavior, and a manual release checklist.

- [ ] **Step 2: Verify every command against project configuration**

Run: `python -m pytest -q`, `npm.cmd run test`, `npm.cmd run build`, `npm.cmd run test:e2e`.

### Task 5: Release gate and push

**Files:**
- Modify: only Phase3/Phase4 implementation and documentation files; leave unrelated existing user files unstaged.

- [ ] **Step 1: Run final checks**

Run: `git diff --check`, backend suite, frontend static suite, production build, E2E suite, and the frontend detector.

- [ ] **Step 2: Review the staged diff**

Run: `git diff --cached --stat` and `git status --short`; confirm no `DROP TABLE`, `DROP COLUMN`, migration, database file, build output, or unrelated documentation is staged.

- [ ] **Step 3: Commit and push the phase**

```bash
git commit -m "feat: complete phase 3 and phase 4 hardening"
git push origin phase1-hardening
```
