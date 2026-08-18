# SellHelp Windows Desktop EXE Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a Windows x64 installer that launches SellHelp locally without Python, Node.js, or network access after installation.

**Architecture:** An Electron main process owns a FastAPI sidecar executable and a single BrowserWindow. The backend binds to loopback, serves `frontend/dist` and `/api`, applies deterministic Alembic migrations, and stores mutable state below `%LOCALAPPDATA%\\SellHelp`. Electron packages that backend and the built frontend into an NSIS installer.

**Tech Stack:** Vue 3, Vite, FastAPI, SQLAlchemy, Alembic, SQLite, PyInstaller, Electron, Electron Builder, Node test runner, pytest, Playwright.

## Global Constraints

- Target Windows 10/11 x64 only; use an unsigned NSIS installer until a signing certificate is supplied.
- The packaged app binds the backend only to `127.0.0.1`, with no Vite server, Uvicorn reload mode, or runtime pip/npm installation.
- Mutable data lives under `%LOCALAPPDATA%\\SellHelp`; installation and uninstallation never delete it.
- Keep the current browser development workflow working; desktop-only behavior is enabled through explicit runtime arguments/environment.
- Use `secrets` and Windows DPAPI for generated desktop JWT secrets; do not weaken the existing 32-character production-secret rule.
- Each production behavior starts with a test that fails for the missing behavior, then receives the smallest implementation that passes.

---

### Task 1: Desktop Runtime Paths And Same-Origin Serving

**Files:**
- Create: `backend/app/desktop_runtime.py`
- Create: `backend/desktop_main.py`
- Create: `backend/tests/test_desktop_runtime.py`
- Modify: `backend/app/database.py:1-57`
- Modify: `backend/app/main.py:1-130`

**Interfaces:**
- Produces `desktop_data_dir() -> Path`, `desktop_static_dir() -> Path | None`, and `is_desktop_mode() -> bool`.
- Produces `parse_desktop_args(argv: Sequence[str] | None) -> argparse.Namespace` with `data_dir`, `static_dir`, and `port` fields.
- Produces `create_app(static_dir: Path | None = None) -> FastAPI`; the module-level `app` remains `create_app()` for Uvicorn.
- Consumes `SELLHELP_DATA_DIR`, `SELLHELP_STATIC_DIR`, and `SELLHELP_DESKTOP_MODE` only when desktop mode is explicitly enabled.

- [ ] **Step 1: Write the failing backend behavior tests**

```python
def test_desktop_runtime_uses_configured_data_directory(monkeypatch, tmp_path):
    monkeypatch.setenv("SELLHELP_DESKTOP_MODE", "1")
    monkeypatch.setenv("SELLHELP_DATA_DIR", str(tmp_path / "SellHelp"))
    assert desktop_data_dir() == tmp_path / "SellHelp"
    assert sqlite_database_path() == tmp_path / "SellHelp" / "data" / "sellhelp.db"


def test_desktop_app_serves_dist_and_preserves_api_routes(tmp_path):
    (tmp_path / "index.html").write_text("<main>SellHelp</main>", encoding="utf-8")
    client = TestClient(create_app(static_dir=tmp_path))
    assert client.get("/api/health").status_code == 200
    assert client.get("/products").status_code == 200
    assert client.get("/unknown-desktop-route").text == "<main>SellHelp</main>"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest backend/tests/test_desktop_runtime.py -v`

Expected: import failure for `app.desktop_runtime` and no static SPA fallback.

- [ ] **Step 3: Implement the minimal runtime module and entry point**

```python
# backend/desktop_main.py
def main(argv=None) -> None:
    args = parse_desktop_args(argv)
    os.environ.update({
        "SELLHELP_DESKTOP_MODE": "1",
        "SELLHELP_DATA_DIR": str(args.data_dir),
        "SELLHELP_STATIC_DIR": str(args.static_dir),
    })
    uvicorn.run("app.main:app", host="127.0.0.1", port=args.port, reload=False)
```

Move the default SQLite path construction behind `sqlite_database_path()`.
Construct the FastAPI application through `create_app()`. Mount static assets
only after router registration; serve a requested static file when it exists
and otherwise serve `index.html`. Set `docs_url=None` and `redoc_url=None`
when desktop mode is enabled.

- [ ] **Step 4: Run the focused tests to verify they pass**

Run: `python -m pytest backend/tests/test_desktop_runtime.py -v`

Expected: all runtime-path and same-origin serving tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/desktop_runtime.py backend/desktop_main.py backend/app/database.py backend/app/main.py backend/tests/test_desktop_runtime.py
git commit -m "feat: add desktop backend runtime"
```

### Task 2: Deterministic Migrations, Desktop Secret, And Logging

**Files:**
- Create: `backend/app/desktop_startup.py`
- Create: `backend/app/desktop_secrets.py`
- Create: `backend/tests/test_desktop_startup.py`
- Modify: `backend/app/main.py:26-46`
- Modify: `backend/requirements.txt`
- Modify: `backend/alembic/env.py:1-60`

**Interfaces:**
- Produces `prepare_desktop_startup() -> StartupResult` before FastAPI begins serving requests.
- Produces `ensure_desktop_jwt_secret(config_dir: Path) -> str` and `load_desktop_jwt_secret(config_dir: Path) -> str`.
- Consumes the active SQLAlchemy URL and Alembic scripts; returns `migration_applied: bool` and `backup_path: Path | None`.
- Produces `configure_desktop_logging(log_dir: Path) -> Path`, with a rotating `sellhelp.log` file.

- [ ] **Step 1: Write the failing startup tests**

```python
def test_new_desktop_database_upgrades_to_head(tmp_path):
    result = prepare_desktop_startup(data_dir=tmp_path)
    assert (tmp_path / "data" / "sellhelp.db").is_file()
    assert result.migration_applied is True
    assert role_codes_from_database(tmp_path / "data" / "sellhelp.db") == {
        "owner", "warehouse_operator", "sales_clerk"
    }


def test_existing_legacy_database_is_backed_up_then_migrated(tmp_path):
    legacy_path = create_legacy_business_database(tmp_path / "data" / "sellhelp.db")
    result = prepare_desktop_startup(data_dir=tmp_path)
    assert result.backup_path is not None and result.backup_path.is_file()
    assert has_table(legacy_path, "users")


def test_desktop_secret_round_trips_for_same_windows_user(tmp_path):
    secret = ensure_desktop_jwt_secret(tmp_path / "config")
    assert len(secret) >= 32
    assert load_desktop_jwt_secret(tmp_path / "config") == secret
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest backend/tests/test_desktop_startup.py -v`

Expected: missing startup/secrets modules and no generated roles in a new desktop database.

- [ ] **Step 3: Implement migration, secret, and logging behavior**

```python
def prepare_desktop_startup(data_dir: Path) -> StartupResult:
    database_path = data_dir / "data" / "sellhelp.db"
    if is_empty_database(database_path):
        alembic_upgrade_head(database_path)
        return StartupResult(True, None)
    if not has_alembic_version(database_path):
        backup_path = sqlite_backup(database_path, data_dir / "backups")
        alembic_stamp(database_path, "d8f13722a89d")
        alembic_upgrade_head(database_path)
        return StartupResult(True, backup_path)
    return StartupResult(alembic_upgrade_if_needed(database_path), None)
```

Implement DPAPI with the Windows `CryptProtectData` and `CryptUnprotectData`
APIs through `ctypes`; store only the encrypted value in `config/jwt-secret.bin`.
Use `logging.handlers.RotatingFileHandler` with UTF-8 encoding and preserve
the existing explicit `SELLHELP_JWT_SECRET` override for non-desktop runs.

- [ ] **Step 4: Run focused tests to verify they pass**

Run: `python -m pytest backend/tests/test_desktop_startup.py -v`

Expected: new, legacy, and already-migrated databases all start correctly; encrypted secrets round-trip; a log file is created.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/desktop_startup.py backend/app/desktop_secrets.py backend/app/main.py backend/alembic/env.py backend/requirements.txt backend/tests/test_desktop_startup.py
git commit -m "feat: prepare desktop data and identity startup"
```

### Task 3: Safe Desktop Backup And Restore

**Files:**
- Modify: `backend/app/routers/system_router.py:15-170`
- Modify: `backend/app/database.py:14-35`
- Modify: `backend/tests/test_system_safety.py`
- Modify: `frontend/src/api/index.js:156-163`
- Create: `frontend/src/utils/desktop.js`
- Modify: `frontend/src/views/Settings.vue:284-325`
- Create: `frontend/tests/desktop-runtime.test.mjs`

**Interfaces:**
- Produces `sqlite_backup(source: Path, target: Path) -> None` and `active_backup_directory() -> Path`.
- Changes `POST /api/system/restore` response to include `restart_required: bool`.
- Produces `requestDesktopBackendRestart() -> Promise<boolean>`; it returns `false` in a normal browser.
- Consumes optional `window.sellhelp.restartBackend()` exposed only by Electron preload.

- [ ] **Step 1: Write failing recovery tests**

```python
def test_backup_uses_active_database_parent_and_sqlite_backup_api(client, configured_database_path):
    result = client.post("/api/system/backup")
    assert result.status_code == 200
    assert Path(result.json()["backup_path"]).parent == configured_database_path.parent / "backups"


def test_restore_disposes_connections_and_requires_desktop_restart(client, backup_fixture):
    result = client.post("/api/system/restore", params={"backup_file": backup_fixture.name})
    assert result.status_code == 200
    assert result.json()["restart_required"] is True
```

```javascript
test('desktop restart helper is inert in a browser and delegates in Electron', async () => {
  assert.equal(await requestDesktopBackendRestart({}), false)
  assert.equal(await requestDesktopBackendRestart({ sellhelp: { restartBackend: async () => true } }), true)
})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest backend/tests/test_system_safety.py -v`

Run: `node --test frontend/tests/desktop-runtime.test.mjs`

Expected: current restore response has no restart flag and configured backups still use the legacy directory.

- [ ] **Step 3: Implement safe backup and restart request**

```python
def sqlite_backup(source: Path, target: Path) -> None:
    with sqlite3.connect(source) as source_connection, sqlite3.connect(target) as target_connection:
        source_connection.backup(target_connection)


def restore_database(...):
    engine.dispose()
    sqlite_backup(backup_path, database_path)
    return {"message": "Database restored", "restart_required": True, ...}
```

Locate `backups` alongside the active file database. On successful restore,
the Settings view calls the desktop bridge when it exists; browser deployments
show a restart instruction instead. Keep filename validation and owner-only
authorization unchanged.

- [ ] **Step 4: Run focused tests to verify they pass**

Run: `python -m pytest backend/tests/test_system_safety.py -v`

Run: `node --test frontend/tests/desktop-runtime.test.mjs`

Expected: backup/restore safety tests and the browser/Electron bridge tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/routers/system_router.py backend/app/database.py backend/tests/test_system_safety.py frontend/src/api/index.js frontend/src/utils/desktop.js frontend/src/views/Settings.vue frontend/tests/desktop-runtime.test.mjs
git commit -m "feat: make desktop recovery restart-safe"
```

### Task 4: Electron Process Owner And Secure Window

**Files:**
- Create: `desktop/package.json`
- Create: `desktop/main.cjs`
- Create: `desktop/preload.cjs`
- Create: `desktop/runtime.cjs`
- Create: `desktop/tests/runtime.test.cjs`
- Create: `desktop/resources/icon.ico`

**Interfaces:**
- Produces `findLoopbackPort() -> Promise<number>`, `backendCommand(resourcesPath, dataDir, port) -> { command, args }`, and `waitForHealth(url, timeoutMs) -> Promise<void>`.
- Produces preload API `window.sellhelp.restartBackend(): Promise<boolean>` only.
- Consumes `process.resourcesPath/backend/SellHelpBackend.exe` and `process.resourcesPath/frontend` in packaged mode.
- Produces one application instance and one backend child process; close and restart operations terminate the owned child process.

- [ ] **Step 1: Write failing Electron runtime tests**

```javascript
test('backend command targets the packaged executable and loopback arguments', () => {
  const result = backendCommand('C:/app/resources', 'C:/Users/a/AppData/Local/SellHelp', 18101)
  assert.equal(result.command, 'C:/app/resources/backend/SellHelpBackend.exe')
  assert.deepEqual(result.args, ['--data-dir', 'C:/Users/a/AppData/Local/SellHelp', '--static-dir', 'C:/app/resources/frontend', '--port', '18101'])
})

test('health wait rejects with the final cause after its deadline', async () => {
  await assert.rejects(waitForHealth('http://127.0.0.1:9/api/health', 25), /Desktop backend did not become healthy/)
})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `node --test desktop/tests/runtime.test.cjs`

Expected: `desktop/runtime.cjs` does not exist.

- [ ] **Step 3: Implement the shell with Electron security defaults**

```javascript
const window = new BrowserWindow({
  show: false,
  webPreferences: {
    preload: path.join(__dirname, 'preload.cjs'),
    contextIsolation: true,
    nodeIntegration: false,
    sandbox: true,
  },
})
```

Use `app.requestSingleInstanceLock()`. Select a loopback port with Node's
`net` module, spawn only the bundled executable, wait for `/api/health`, then
load the local HTTP URL. Handle a second launch by focusing the existing
window. On failure, write the child stderr to the desktop log and display a
native error dialog. The preload must expose no filesystem, shell, or generic
IPC access. Generate the application icon through the approved image asset
workflow and convert it to `icon.ico` before packaging.

- [ ] **Step 4: Run focused tests to verify they pass**

Run: `node --test desktop/tests/runtime.test.cjs`

Expected: command construction and health-timeout behavior pass without loading Electron.

- [ ] **Step 5: Commit**

```powershell
git add desktop
git commit -m "feat: add secure Electron desktop shell"
```

### Task 5: Reproducible Backend Bundle And NSIS Installer

**Files:**
- Create: `backend/SellHelpBackend.spec`
- Create: `backend/requirements-build.txt`
- Create: `scripts/build-desktop.ps1`
- Modify: `backend/requirements.txt`
- Modify: `desktop/package.json`
- Modify: `README.md`
- Modify: `README-OPERATE.md`

**Interfaces:**
- Produces `backend/dist/SellHelpBackend/SellHelpBackend.exe` through `pyinstaller --noconfirm SellHelpBackend.spec`.
- Produces `desktop/release/SellHelp Setup <version>.exe` through `electron-builder --win nsis`.
- Consumes the built `frontend/dist`, bundled Alembic files, `alembic.ini`, and backend package modules.
- Produces `build-desktop.ps1` exit code zero only when frontend, backend, and installer builds all succeed.

- [ ] **Step 1: Write failing build-contract tests**

```javascript
test('desktop package defines a Windows NSIS build without unpackaged backend sources', () => {
  const config = JSON.parse(readFileSync('desktop/package.json', 'utf8'))
  assert.equal(config.build.win.target[0], 'nsis')
  assert.equal(config.build.extraResources.some(item => item.to === 'backend'), true)
})
```

```python
def test_pyinstaller_build_produces_a_backend_executable(tmp_path):
    completed = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--distpath", str(tmp_path / "dist"), "SellHelpBackend.spec"],
        cwd=BACKEND_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert (tmp_path / "dist" / "SellHelpBackend" / "SellHelpBackend.exe").is_file()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `node --test desktop/tests/build-contract.test.cjs`

Run: `python -m pytest backend/tests/test_desktop_bundle.py -v`

Expected: missing package/build spec files.

- [ ] **Step 3: Implement package metadata and one build command**

```powershell
npm --prefix frontend ci
npm --prefix frontend run build
python -m PyInstaller --noconfirm backend\SellHelpBackend.spec
npm --prefix desktop ci
npm --prefix desktop run dist
```

Pin direct backend production dependencies to exact tested versions and keep
PyInstaller in the build-only requirements file. Configure Electron Builder
to include `backend/dist/SellHelpBackend`, `frontend/dist`, the icon, product
version, NSIS uninstall metadata, and no runtime source checkout. Document
the unsigned installer limitation and that uninstall preserves LocalAppData.

- [ ] **Step 4: Run focused tests to verify they pass**

Run: `node --test desktop/tests/build-contract.test.cjs`

Run: `python -m pytest backend/tests/test_desktop_bundle.py -v`

Expected: packaging contract tests pass before the expensive build.

- [ ] **Step 5: Commit**

```powershell
git add backend/SellHelpBackend.spec backend/requirements-build.txt backend/requirements.txt scripts/build-desktop.ps1 desktop/package.json desktop/tests/build-contract.test.cjs backend/tests/test_desktop_bundle.py README.md README-OPERATE.md
git commit -m "build: package SellHelp as a Windows installer"
```

### Task 6: Packaged Application Smoke Verification

**Files:**
- Create: `desktop/tests/packaged-smoke.cjs`
- Modify: `frontend/tests/e2e/run.mjs`
- Modify: `README-OPERATE.md`

**Interfaces:**
- Consumes `desktop/release/SellHelp Setup <version>.exe` and a temporary `%LOCALAPPDATA%` equivalent.
- Produces an automated packaged smoke result covering backend launch, same-origin UI loading, loopback-only health, data persistence, export download, and child-process cleanup.
- Consumes existing `frontend/tests/e2e/critical-workflow.spec.mjs` as the browser business-flow regression suite.

- [ ] **Step 1: Write the failing packaged smoke test**

```javascript
test('installed desktop app starts a loopback backend and retains data after restart', async () => {
  const app = await launchPackagedApp({ userDataDir: temporaryDataDir })
  await expectHealth('127.0.0.1')
  await createProductThroughWindow(app.window, 'desktop-smoke-product')
  await app.restart()
  await expectProductThroughWindow(app.window, 'desktop-smoke-product')
  await expectBackendListenerAddress(app.backendProcessId, '127.0.0.1')
})
```

- [ ] **Step 2: Run the smoke test to verify it fails before packaging**

Run: `node --test desktop/tests/packaged-smoke.cjs`

Expected: clear failure that no packaged installer is available.

- [ ] **Step 3: Implement the test harness and build the installer**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build-desktop.ps1
node --test desktop/tests/packaged-smoke.cjs
```

Use a temporary test data directory. The harness must wait for the native
window, use only the packaged local UI, and delete only its own temporary
directory after closing the app. Extend operating instructions with the clean
machine checklist: no Python/Node, offline launch, upgrade preservation,
uninstall preservation, backup restore, PDF/XLSX export, and print.

- [ ] **Step 4: Run complete release verification**

Run: `python -m pytest backend/tests -v`

Run: `npm --prefix frontend test`

Run: `npm --prefix frontend run build`

Run: `npm --prefix frontend run test:e2e`

Run: `node --test desktop/tests/runtime.test.cjs desktop/tests/build-contract.test.cjs desktop/tests/packaged-smoke.cjs`

Expected: all tests pass and the installer is produced under `desktop/release`.

- [ ] **Step 5: Commit**

```powershell
git add desktop/tests/packaged-smoke.cjs frontend/tests/e2e/run.mjs README-OPERATE.md
git commit -m "test: verify packaged desktop workflow"
```

## Plan Self-Review

- Scope coverage: Tasks 1-5 implement all architecture, persistence,
  migration, security, backup, diagnostics, build, and installer requirements
  in the approved design. Task 6 verifies every listed acceptance criterion
  that can run in this workspace; real Authenticode signing remains excluded
  because it requires an external certificate.
- Placeholder scan: no deferred implementation phrases or unspecified test
  steps remain.
- Interface consistency: Electron invokes `desktop_main.py` with `--data-dir`,
  `--static-dir`, and `--port`; its FastAPI static serving retains relative
  `/api`; backup responses request the preload bridge defined in Task 4.
