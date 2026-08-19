# Desktop Automatic Backups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically create and retain safe local SQLite backups for the desktop application, and show their status in Settings.

**Architecture:** A desktop-only backup service owns due calculation, online SQLite copies, persisted status, and automatic-file retention. An APScheduler wrapper runs the service without blocking startup and is started/stopped by FastAPI lifespan. The system router exposes the safe status projection, while the existing Settings backup tab displays it beside manual backup controls.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, SQLite backup API, APScheduler, Vue 3, Element Plus, Node built-in test runner.

## Global Constraints

- Enable automatic backups only when `SELLHELP_DESKTOP_MODE=1`; browser and network-server modes must not schedule writes.
- Use the existing SQLite backup API; never copy a live `.db` file directly.
- Store automatic copies under the active database parent `backups` directory; packaged desktop data is `%LOCALAPPDATA%\\SellHelp\\backups`.
- Check hourly and copy only when the last successful automatic backup is at least 24 hours old.
- Retain exactly the newest 14 `sellhelp_auto_` backups. Never delete `yingtai_backup_`, `pre_restore_`, or pre-migration backups.
- Reuse `SystemConfig`; no database migration or dependency addition is allowed.
- Backup failures must be logged and persisted, must clean up their partial automatic file, and must not prevent serving requests or a later retry.
- Preserve existing owner-only system-route authorization and filename/path traversal protections.
- Keep user-owned untracked planning documents out of commits.

---

## File Structure

- Create `backend/app/services/desktop_backup_service.py`: backup policy, state serialization, SQLite copy, automatic-file retention, and status projection.
- Create `backend/app/services/desktop_backup_scheduler.py`: desktop-only APScheduler adapter with an immediate nonblocking due check and hourly repeats.
- Create `backend/tests/test_desktop_backup_service.py`: file-based SQLite, due-state, retention, and error-cleanup coverage.
- Create `backend/tests/test_desktop_backup_scheduler.py`: scheduler isolation and FastAPI lifespan integration coverage.
- Modify `backend/app/main.py`: start/stop the desktop scheduler around the existing lifecycle.
- Modify `backend/app/routers/system_router.py`: accept automatic backup names and provide `GET /api/system/backup-status`.
- Modify `backend/tests/test_system_safety.py`: protect the new filename format and status response contract.
- Modify `frontend/src/api/index.js`: export the backup-status request helper.
- Modify `frontend/src/views/Settings.vue`: load and render automatic-backup state in the existing backup tab.
- Create `frontend/tests/desktop-backup-ui.test.mjs`: API request and Settings source contract checks.
- Modify `frontend/package.json`: include the new frontend contract test in `npm.cmd test`.
- Modify `README-OPERATE.md`: document local automatic backup, retention, failure behavior, and the offline-copy limitation.

## Task 1: Automatic Backup Service

**Files:**
- Create: `backend/app/services/desktop_backup_service.py`
- Create: `backend/tests/test_desktop_backup_service.py`

**Interfaces:**
- Consumes: `app.database.sqlite_backup`, file-based SQLite paths, `SystemConfig`, a SQLAlchemy `Session`, and a clock returning timezone-aware UTC `datetime`.
- Produces: `DesktopBackupService(database_path, backup_dir, now, backup_function)` with `run_if_due(db) -> dict` and `status(db, enabled: bool) -> dict`.
- Produces: `DesktopBackupService.for_active_database() -> DesktopBackupService` and `DesktopBackupService.disabled_status(db) -> dict` for the router's active and non-desktop branches.
- Produces: constants `AUTO_BACKUP_PREFIX = "sellhelp_auto_"`, `AUTO_BACKUP_INTERVAL_HOURS = 24`, `AUTO_BACKUP_RETENTION_COUNT = 14`, and `AUTO_BACKUP_STATUS_KEY = "desktop_automatic_backup"`.

- [x] **Step 1: Write the failing service tests**

Build `file_session_factory(database_path)` in this test module with a SQLAlchemy engine for the same file database and create `SystemConfig.__table__` on that engine. Do not use the shared in-memory `db_session` fixture, because the service state and SQLite source must exercise one real file-backed database.

```python
def test_due_backup_copies_database_records_status_and_retains_manual_files(tmp_path, session_factory):
    database_path = create_file_database(tmp_path / "data" / "sellhelp.db", value="preserved")
    backup_dir = database_path.parent / "backups"
    backup_dir.mkdir()
    (backup_dir / "yingtai_backup_20260818_120000.db").touch()
    service = DesktopBackupService(database_path, backup_dir, now=fixed_utc_now)

    result = service.run_if_due(session_factory())

    assert result["created"] is True
    created = backup_dir / result["last_success"]["filename"]
    with sqlite3.connect(created) as connection:
        assert connection.execute("SELECT value FROM recovery_check").fetchone() == ("preserved",)
    assert (backup_dir / "yingtai_backup_20260818_120000.db").exists()
    assert result["last_success"]["size"] == created.stat().st_size


def test_retention_keeps_fourteen_automatic_files_and_never_removes_protection_files(tmp_path, session_factory):
    database_path = create_file_database(tmp_path / "data" / "sellhelp.db")
    backup_dir = database_path.parent / "backups"
    backup_dir.mkdir()
    create_timestamped_auto_files(backup_dir, count=14)
    manual = backup_dir / "yingtai_backup_20260818_120000.db"
    pre_restore = backup_dir / "pre_restore_20260818_120000.db"
    manual.touch()
    pre_restore.touch()

    DesktopBackupService(database_path, backup_dir, now=fixed_utc_now).run_if_due(session_factory())

    assert len(list(backup_dir.glob("sellhelp_auto_*.db"))) == 14
    assert manual.exists() and pre_restore.exists()


def test_failed_backup_removes_partial_file_records_failure_and_can_retry(tmp_path, session_factory):
    database_path = create_file_database(tmp_path / "data" / "sellhelp.db")
    service = DesktopBackupService(database_path, database_path.parent / "backups", backup_function=write_partial_then_raise)

    failure = service.run_if_due(session_factory())

    assert failure["created"] is False
    assert failure["last_failure"]["error_type"] == "OSError"
    assert not list((database_path.parent / "backups").glob("sellhelp_auto_*.db"))
```

- [x] **Step 2: Run the service tests to verify they fail**

Run: `python -m pytest backend/tests/test_desktop_backup_service.py -v`

Expected: FAIL because `app.services.desktop_backup_service` and `DesktopBackupService` do not exist.

- [x] **Step 3: Write the minimal service implementation**

```python
class DesktopBackupService:
    def __init__(self, database_path, backup_dir, *, now=utc_now, backup_function=sqlite_backup):
        self.database_path = Path(database_path)
        self.backup_dir = Path(backup_dir)
        self.now = now
        self.backup_function = backup_function

    def run_if_due(self, db):
        state = self._load_state(db)
        if not self._is_due(state):
            return {"created": False, **self.status(db, enabled=True)}
        target = self._next_backup_path()
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            self.backup_function(self.database_path, target)
            self._record_success(db, target)
            self._prune_automatic_backups()
        except Exception as exc:
            target.unlink(missing_ok=True)
            self._record_failure(db, exc)
        return {"created": target.exists(), **self.status(db, enabled=True)}

    @classmethod
    def for_active_database(cls):
        return cls(Path(get_active_sqlite_db_path()), active_backup_directory())

    @classmethod
    def disabled_status(cls, db):
        return cls._status_payload(cls._load_persisted_state(db), enabled=False)
```

Persist only `last_success` (`completed_at`, `filename`, `size`) and `last_failure` (`occurred_at`, `error_type`) as JSON. Parse timestamps as UTC, treat absent or malformed state as overdue, and never remove a non-automatic filename.

- [x] **Step 4: Run the service tests to verify they pass**

Run: `python -m pytest backend/tests/test_desktop_backup_service.py -v`

Expected: PASS. Confirm generated backups are readable SQLite data, the 15th automatic copy removes only the oldest automatic file, recent success skips copying, and a later healthy service retries after a stored failure.

- [x] **Step 5: Commit the service slice**

```powershell
git add backend/app/services/desktop_backup_service.py backend/tests/test_desktop_backup_service.py
git commit -m "feat: add desktop automatic backup service"
```

## Task 2: Background Scheduler and Application Lifecycle

**Files:**
- Create: `backend/app/services/desktop_backup_scheduler.py`
- Create: `backend/tests/test_desktop_backup_scheduler.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `DesktopBackupService`, `SessionLocal`, `BackgroundScheduler`, and `is_desktop_mode()`.
- Produces: `DesktopBackupScheduler(scheduler=None, session_factory=SessionLocal, service_factory=...)` with `start()`, `shutdown()`, and `run_scheduled_backup()`.
- Produces: `desktop_backup_scheduler`, started by `initialize_database()` after `init_db()` only in desktop mode and stopped by FastAPI lifespan shutdown.

- [x] **Step 1: Write the failing scheduler and lifespan tests**

```python
def test_desktop_scheduler_submits_immediate_hourly_job_and_closes_its_session():
    backend = FakeBackgroundScheduler()
    sessions, calls = [], []
    scheduler = DesktopBackupScheduler(
        scheduler=backend,
        session_factory=lambda: tracked_session(sessions),
        service_factory=lambda: recording_service(calls),
    )

    scheduler.start()
    scheduler.run_scheduled_backup()
    scheduler.shutdown()

    assert backend.added_jobs[0][2]["id"] == "desktop_automatic_backup_due_check"
    assert backend.added_jobs[0][2]["replace_existing"] is True
    assert backend.added_jobs[0][2]["next_run_time"] is not None
    assert calls == [sessions[0]] and sessions[0].closed is True
    assert backend.shutdown_wait_values == [False]


def test_lifecycle_starts_desktop_scheduler_only_after_database_setup(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "init_db", lambda: calls.append("init_db"))
    monkeypatch.setattr(main.desktop_backup_scheduler, "start", lambda: calls.append("backup_start"))
    monkeypatch.setattr(main.desktop_backup_scheduler, "shutdown", lambda: calls.append("backup_stop"))
    monkeypatch.setattr(main, "is_desktop_mode", lambda: True)

    main.initialize_database()
    main.shutdown_runtime_services()

    assert calls[:2] == ["init_db", "backup_start"]
    assert "backup_stop" in calls
```

- [x] **Step 2: Run the scheduler tests to verify they fail**

Run: `python -m pytest backend/tests/test_desktop_backup_scheduler.py -v`

Expected: FAIL because `DesktopBackupScheduler` and `shutdown_runtime_services` do not exist.

- [x] **Step 3: Write the minimal scheduler and lifecycle wiring**

```python
class DesktopBackupScheduler:
    def start(self):
        self.scheduler.add_job(
            self.run_scheduled_backup, "interval", hours=1,
            id="desktop_automatic_backup_due_check", replace_existing=True,
            next_run_time=datetime.now(timezone.utc), coalesce=True,
        )
        if not self._started:
            self.scheduler.start()
            self._started = True

    def run_scheduled_backup(self):
        db = self.session_factory()
        try:
            self.service_factory().run_if_due(db)
        except Exception as exc:
            logger.error("Desktop automatic backup failed: %s", type(exc).__name__)
        finally:
            db.close()
```

In `main.py`, call `desktop_backup_scheduler.start()` only after `init_db()` and only in desktop mode. Add `shutdown_runtime_services()` to stop the desktop scheduler before the existing market scheduler shutdown, and call it from the lifespan `finally` block. Preserve the existing market scheduler environment switch and startup order.

- [x] **Step 4: Run scheduler and existing lifecycle tests to verify they pass**

Run: `python -m pytest backend/tests/test_desktop_backup_scheduler.py backend/tests/test_market_sync_scheduler.py backend/tests/test_desktop_startup.py -v`

Expected: PASS. Confirm non-desktop mode never starts the backup scheduler and lifecycle shutdown is nonblocking.

- [x] **Step 5: Commit the scheduler slice**

```powershell
git add backend/app/services/desktop_backup_scheduler.py backend/app/main.py backend/tests/test_desktop_backup_scheduler.py
git commit -m "feat: schedule desktop automatic backups"
```

## Task 3: Safe Status Endpoint and Backup Name Integration

**Files:**
- Modify: `backend/app/routers/system_router.py`
- Modify: `backend/tests/test_system_safety.py`
- Modify: `backend/tests/test_auth_permissions.py`

**Interfaces:**
- Consumes: `DesktopBackupService.status(db, enabled)` and the existing `SystemConfig` session dependency.
- Produces: `GET /api/system/backup-status` response fields `enabled`, `interval_hours`, `retention_count`, `is_due`, `last_success`, and `last_failure`.
- Produces: backup filename acceptance for `sellhelp_auto_YYYYMMDD_HHMMSSffffff.db` only; all existing unsafe-name rejections remain intact.

- [x] **Step 1: Write the failing route and authorization tests**

```python
def test_backup_status_exposes_policy_without_leaking_database_path(client, db_session, monkeypatch, tmp_path):
    configure_active_file_database(monkeypatch, tmp_path)
    monkeypatch.setenv("SELLHELP_DESKTOP_MODE", "1")
    db_session.add(SystemConfig(
        key="desktop_automatic_backup",
        value=json.dumps({"last_success": {"completed_at": "2026-08-19T00:00:00+00:00", "filename": "sellhelp_auto_20260819_000000000000.db", "size": 32}}),
    ))
    db_session.commit()

    response = client.get("/api/system/backup-status")

    assert response.status_code == 200
    assert response.json()["enabled"] is True
    assert response.json()["retention_count"] == 14
    assert "path" not in json.dumps(response.json())


def test_backup_operations_accept_only_the_automatic_backup_filename_format(client, tmp_path, monkeypatch):
    filename = "sellhelp_auto_20260819_000000000000.db"
    configure_active_file_database(monkeypatch, tmp_path)
    (database.active_backup_directory() / filename).touch()

    assert client.get(f"/api/system/backups/{filename}").status_code == 200
    assert client.get("/api/system/backups/sellhelp_auto_.._outside.db").status_code == 400
```

Extend the existing multi-role permission test with `GET /api/system/backup-status` for warehouse and sales users, asserting the same owner-only protection as the rest of `/api/system`.

- [x] **Step 2: Run the route tests to verify they fail**

Run: `python -m pytest backend/tests/test_system_safety.py backend/tests/test_auth_permissions.py -v`

Expected: FAIL with `404` for `/api/system/backup-status` and `400` for the valid automatic filename.

- [x] **Step 3: Write the minimal route changes**

```python
@router.get("/backup-status")
def get_backup_status(db: Session = Depends(get_db)):
    if not is_desktop_mode():
        return DesktopBackupService.disabled_status(db)
    return DesktopBackupService.for_active_database().status(db, enabled=True)


_BACKUP_FILENAME = re.compile(
    r"(?:(?:yingtai_backup|pre_restore)_\d{8}_\d{6}|sellhelp_auto_\d{8}_\d{12})\.db"
)
```

Construct `DesktopBackupService.for_active_database()` from `get_active_sqlite_db_path()` and `active_backup_directory()`. Keep the route under `/api/system`, so the existing owner rule applies. The disabled response uses the same policy fields, reports `enabled: false`, and performs no backup file I/O.

- [x] **Step 4: Run the route tests to verify they pass**

Run: `python -m pytest backend/tests/test_system_safety.py backend/tests/test_auth_permissions.py -v`

Expected: PASS. Confirm safe download remains constrained to the active backup directory and non-owner requests remain `403` when standalone mode is disabled.

- [x] **Step 5: Commit the route slice**

```powershell
git add backend/app/routers/system_router.py backend/tests/test_system_safety.py backend/tests/test_auth_permissions.py
git commit -m "feat: report desktop backup status"
```

## Task 4: Settings Status, API Client, and Operations Documentation

**Files:**
- Modify: `frontend/src/api/index.js`
- Modify: `frontend/src/views/Settings.vue`
- Create: `frontend/tests/desktop-backup-ui.test.mjs`
- Modify: `frontend/package.json`
- Modify: `README-OPERATE.md`

**Interfaces:**
- Consumes: `GET /api/system/backup-status` and its fields from Task 3.
- Produces: `getBackupStatus()` API helper and a `backupStatus` Settings state loaded with the existing backup list.
- Produces: user-facing status for enabled, last success, 14-copy retention, and latest failure; no browser-side scheduler or direct filesystem access.

- [x] **Step 1: Write the failing frontend API and Settings contract tests**

```javascript
test('getBackupStatus uses the protected automatic backup status route', async () => {
  await api.getBackupStatus()

  assert.deepEqual({ method: lastRequest().method, url: lastRequest().url }, {
    method: 'get', url: '/system/backup-status'
  })
})

test('Settings loads and renders automatic backup status beside manual backups', async () => {
  const source = await readFile(new URL('../src/views/Settings.vue', import.meta.url), 'utf8')

  assert.match(source, /getBackupStatus/)
  assert.match(source, /backupStatus/)
  assert.match(source, /保留 14 份自动备份/)
  assert.match(source, /last_failure/)
})
```

- [x] **Step 2: Run the frontend tests to verify they fail**

Run: `node --test tests/external-market-api.test.mjs tests/desktop-backup-ui.test.mjs`

Expected: FAIL because `getBackupStatus`, `backupStatus`, and the Settings automatic-backup content do not exist.

- [x] **Step 3: Write the minimal Settings and documentation changes**

```javascript
export const getBackupStatus = () => api.get('/system/backup-status')

const backupStatus = ref(null)
const loadBackups = async () => {
  backupLoading.value = true
  try {
    const [backupsResult, status] = await Promise.all([getBackups(), getBackupStatus()])
    backups.value = backupsResult.backups || []
    backupStatus.value = status
  } finally {
    backupLoading.value = false
  }
}
```

Add an unframed status description immediately above the existing backup statistics. Show the 24-hour/14-copy policy only when `enabled` is true; otherwise show that automatic desktop backups are unavailable in the current mode. Render the last failure as a warning alert without exposing a filesystem path. Add `frontend/tests/desktop-backup-ui.test.mjs` to the existing Node test command. Update `README-OPERATE.md` to state that automatic copies are local only, run while the desktop app is open, retain 14 automatic copies, and should still be copied to separate storage for device-loss protection.

- [x] **Step 4: Run frontend tests and the production build to verify they pass**

Run: `npm.cmd test`

Expected: PASS, including the API request and Settings source contracts.

Run: `npm.cmd run build`

Expected: exit code `0`; record only pre-existing Sass or bundle-size warnings.

- [x] **Step 5: Commit the UI and documentation slice**

```powershell
git add frontend/src/api/index.js frontend/src/views/Settings.vue frontend/tests/desktop-backup-ui.test.mjs frontend/package.json README-OPERATE.md
git commit -m "feat: show desktop automatic backup status"
```

## Task 5: Full Regression and Release Evidence

**Files:**
- Modify: `docs/superpowers/plans/2026-08-19-desktop-automatic-backups.md` (mark completed checks only)

**Interfaces:**
- Consumes: all completed Tasks 1-4.
- Produces: fresh test, build, and diff evidence; no additional runtime behavior.

- [x] **Step 1: Run the complete backend suite**

Run: `python -m pytest backend/tests -q`

Expected: all backend tests pass with no new warnings or failures.

- [x] **Step 2: Run all desktop runtime contracts**

Run: `npm.cmd --prefix desktop test`

Expected: all Electron lifecycle, backend-launch, packaging-contract, and smoke-helper tests pass without generating or installing an artifact.

- [x] **Step 3: Run frontend suite and production build**

Run: `npm.cmd test`

Expected: all frontend Node tests pass.

Run: `npm.cmd run build`

Expected: exit code `0`.

- [x] **Step 4: Inspect scope and commit the verification record**

Run: `git diff --check f6b6655..HEAD`

Expected: no whitespace errors.

Run: `git status --short`

Expected: only the pre-existing untracked planning documents remain; do not stage or remove them.

Mark only verified checkboxes in this plan, then commit the plan record:

```powershell
git add docs/superpowers/plans/2026-08-19-desktop-automatic-backups.md
git commit -m "docs: record automatic backup verification"
```
