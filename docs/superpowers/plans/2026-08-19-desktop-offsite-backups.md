# Desktop Offsite Backups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replicate verified automatic SQLite backups to one owner-selected external directory without weakening local recovery.

**Architecture:** `DesktopBackupService` remains responsible for local online copies. A separate offsite service stores one target and atomically copies the latest finished `sellhelp_auto_*.db` on every scheduler tick. Owner-only system routes redact configuration, while Electron provides the sole directory-picker capability.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy/SQLite, APScheduler, Electron 43, Vue 3, Element Plus, Node built-in test runner.

## Global Constraints

- Enable this only under `SELLHELP_DESKTOP_MODE=1`; do not add migrations, runtime dependencies, cloud credentials, paid services, or signing changes.
- Copy only completed local automatic backup files, support one existing writable absolute target, and retain fourteen automatic replica files without deleting non-automatic files.
- A replica error removes temporary output, persists a safe error type, and never prevents local backup creation or business requests.
- Full paths never appear in the API/UI; existing `/api/system` owner authorization remains the only role gate.
- Electron exposes one fixed no-argument picker IPC and no general filesystem capability.

---

### Task 1: Implement an Isolated Offsite Replica Service

**Files:**
- Create: `backend/app/services/desktop_offsite_backup_service.py`
- Create: `backend/tests/test_desktop_offsite_backup_service.py`

**Interfaces:**
- `DesktopOffsiteBackupService(local_backup_dir, now=utc_now, copy_function=shutil.copy2)`.
- `configure(db, directory)`, `disable(db)`, `sync_latest(db)`, and `status(db, enabled)`.
- Status fields: `enabled`, `configured`, `directory_name`, `retention_count`, `is_pending`, `last_success`, `last_failure`.

- [ ] **Step 1: Write failing file-backed tests**

```python
def test_replica_is_readable_and_keeps_only_automatic_files(tmp_path, session_factory):
    source = create_sqlite_backup(tmp_path / "local" / "sellhelp_auto_20260819_120000000000.db")
    target = tmp_path / "external"
    target.mkdir()
    create_automatic_files(target, count=14)
    protected = target / "notes.txt"
    protected.write_text("keep", encoding="utf-8")
    with session_factory() as db:
        service = DesktopOffsiteBackupService(source.parent, now=lambda: NOW)
        service.configure(db, target)
        result = service.sync_latest(db)
    with sqlite3.connect(target / source.name) as copy:
        assert copy.execute("SELECT value FROM recovery_check").fetchone() == ("preserved",)
    assert result["last_success"]["filename"] == source.name
    assert len(list(target.glob("sellhelp_auto_*.db"))) == 14
    assert protected.exists()

def test_failure_cleans_temp_and_retry_succeeds(tmp_path, session_factory):
    local, target = tmp_path / "local", tmp_path / "external"
    create_sqlite_backup(local / "sellhelp_auto_20260819_120000000000.db")
    target.mkdir()
    with session_factory() as db:
        failing = DesktopOffsiteBackupService(local, copy_function=copy_partial_then_raise)
        failing.configure(db, target)
        failed = failing.sync_latest(db)
        retried = DesktopOffsiteBackupService(local).sync_latest(db)
    assert failed["last_failure"]["error_type"] == "OSError"
    assert not list(target.glob("*.tmp"))
    assert retried["last_failure"] is None
```

Also cover relative/missing/unwritable target rejection, no source as pending, basename-only status, and disable retaining files.

- [ ] **Step 2: Run RED test**

Run: `python -m pytest backend/tests/test_desktop_offsite_backup_service.py -v`

Expected: module import failure.

- [ ] **Step 3: Implement the minimal service**

```python
def sync_latest(self, db: Session) -> dict:
    state = self._load_state(db)
    directory, source = self._configured_directory(state), self._latest_local_backup()
    if directory is None or source is None:
        return self._status_payload(state, enabled=True, pending=directory is not None)
    temporary = directory / f".{source.name}.{uuid4().hex}.tmp"
    try:
        self.copy_function(source, temporary)
        self._assert_readable_sqlite(temporary)
        os.replace(temporary, directory / source.name)
        self._save_state(db, self._with_success(state, source))
        self._prune_automatic_replicas(directory)
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        self._save_state(db, self._with_failure(state, exc))
    return self.status(db, enabled=True)
```

Use `desktop_offsite_backup` in `SystemConfig`. Validate an absolute existing directory through a UUID create/unlink probe. Require `PRAGMA quick_check` to return `ok`, return only the directory basename, and sort only automatic filenames for pruning.

- [ ] **Step 4: Run GREEN test and commit**

Run: `python -m pytest backend/tests/test_desktop_offsite_backup_service.py -v`

Expected: copy, validation, retention, retry, and redaction checks pass. Commit `feat: replicate desktop backups offsite` with only the two Task 1 files.

### Task 2: Schedule Replication and Add Protected API

**Files:**
- Modify: `backend/app/services/desktop_backup_scheduler.py`
- Modify: `backend/app/routers/system_router.py`
- Modify: `backend/tests/test_desktop_backup_scheduler.py`
- Modify: `backend/tests/test_system_safety.py`
- Modify: `backend/tests/test_auth_permissions.py`

**Interfaces:**
- Scheduler executes `local.run_if_due(db)` before `offsite.sync_latest(db)` in one short-lived session.
- API routes: `GET /api/system/backup-replica-status`, `PUT /api/system/backup-replica?directory=...`, and `DELETE /api/system/backup-replica`.

- [ ] **Step 1: Write failing scheduler and API tests**

```python
def test_scheduler_runs_local_before_offsite_and_closes_session():
    calls, sessions = [], []
    scheduler = DesktopBackupScheduler(
        scheduler=FakeBackgroundScheduler(),
        session_factory=lambda: sessions.append(TrackedSession()) or sessions[-1],
        service_factory=lambda: RecordingService("local", calls),
        offsite_service_factory=lambda: RecordingService("offsite", calls),
    )
    scheduler.run_scheduled_backup()
    assert calls == [("local", sessions[0]), ("offsite", sessions[0])]
    assert sessions[0].closed is True

def test_replica_status_redacts_path_and_browser_mode_rejects_write(client, monkeypatch, tmp_path):
    target = tmp_path / "external"
    target.mkdir()
    monkeypatch.setenv("SELLHELP_DESKTOP_MODE", "1")
    assert client.put("/api/system/backup-replica", params={"directory": str(target)}).status_code == 200
    response = client.get("/api/system/backup-replica-status")
    assert response.json()["directory_name"] == "external"
    assert str(target) not in json.dumps(response.json())
    monkeypatch.delenv("SELLHELP_DESKTOP_MODE", raising=False)
    assert client.put("/api/system/backup-replica", params={"directory": str(target)}).status_code == 400
```

Add assertions that warehouse/sales receive `403` from all three routes, DELETE retains target files, and browser GET is disabled without probing a directory.

- [ ] **Step 2: Run RED test**

Run: `python -m pytest backend/tests/test_desktop_backup_scheduler.py backend/tests/test_system_safety.py backend/tests/test_auth_permissions.py -v`

Expected: absent scheduler collaborator and 404 routes.

- [ ] **Step 3: Implement local-first scheduler and desktop-only routes**

```python
def run_scheduled_backup(self):
    db = self.session_factory()
    try:
        self.service_factory().run_if_due(db)
        self.offsite_service_factory().sync_latest(db)
    except Exception as exc:
        logger.error("Desktop automatic backup scheduler failed: %s", type(exc).__name__)
    finally:
        db.close()
```

Inject `offsite_service_factory=DesktopOffsiteBackupService.for_active_database`. GET returns disabled status outside desktop mode; PUT/DELETE return HTTP 400 outside desktop mode. Map only service validation `ValueError` to 400 and retain existing middleware authorization.

- [ ] **Step 4: Run GREEN test and commit**

Run: `python -m pytest backend/tests/test_desktop_offsite_backup_service.py backend/tests/test_desktop_backup_scheduler.py backend/tests/test_system_safety.py backend/tests/test_auth_permissions.py -v`

Expected: order, route protection, path redaction, and browser isolation pass. Commit `feat: configure desktop offsite backups` with Task 2 files.

### Task 3: Add a Restricted Electron Directory Picker

**Files:**
- Create: `desktop/directory-picker.cjs`
- Create: `desktop/tests/directory-picker.test.cjs`
- Modify: `desktop/main.cjs`
- Modify: `desktop/preload.cjs`
- Modify: `desktop/package.json`

**Interfaces:**
- `selectedDirectory(result) -> string | null`.
- `window.sellhelp.selectBackupDirectory() -> Promise<string | null>`, invoking `sellhelp:select-backup-directory` with no arguments.

- [ ] **Step 1: Write failing Node tests**

```javascript
test('picker normalises one native directory result', () => {
  assert.equal(selectedDirectory({ canceled: false, filePaths: ['D:/copies'] }), 'D:/copies')
  assert.equal(selectedDirectory({ canceled: true, filePaths: ['D:/ignored'] }), null)
  assert.equal(selectedDirectory({ canceled: false, filePaths: [] }), null)
})

test('preload picker accepts no renderer arguments', async () => {
  const source = await readFile(new URL('../preload.cjs', import.meta.url), 'utf8')
  assert.match(source, /selectBackupDirectory: async \(\) => ipcRenderer\.invoke\('sellhelp:select-backup-directory'\)/)
  assert.doesNotMatch(source, /invoke\('sellhelp:select-backup-directory',/)
})
```

- [ ] **Step 2: Run RED test**

Run: `node --test desktop/tests/directory-picker.test.cjs`

Expected: module and bridge are absent.

- [ ] **Step 3: Implement the fixed picker boundary**

```javascript
function selectedDirectory(result) {
  const first = result?.canceled ? null : result?.filePaths?.[0]
  return typeof first === 'string' && first.length > 0 ? first : null
}

async function selectBackupDirectory(event) {
  if (!mainWindow || event.sender !== mainWindow.webContents) return null
  return selectedDirectory(await dialog.showOpenDialog(mainWindow, {
    title: 'Choose backup replica directory', properties: ['openDirectory'],
  }))
}
```

Register the fixed IPC in main, expose only the no-argument bridge through the frozen preload object, add the test to the desktop test script, and include the helper in Electron Builder files.

- [ ] **Step 4: Run GREEN test and commit**

Run: `npm.cmd --prefix desktop test`

Run: `node --check desktop/main.cjs; node --check desktop/preload.cjs; node --check desktop/directory-picker.cjs`

Expected: existing desktop contracts remain green. Commit `feat: select desktop backup replica directory` with Task 3 files.

### Task 4: Settings, API Client, and Operations Guide

**Files:**
- Modify: `frontend/src/api/index.js`
- Modify: `frontend/src/views/Settings.vue`
- Create: `frontend/tests/desktop-offsite-backup-ui.test.mjs`
- Modify: `frontend/package.json`
- Modify: `README-OPERATE.md`

**Interfaces:**
- `getBackupReplicaStatus()`, `configureBackupReplica(directory)`, `disableBackupReplica()`.
- `replicaStatus` and `chooseBackupReplicaDirectory()` in the existing backup tab.

- [ ] **Step 1: Write failing frontend contracts**

```javascript
test('replica helpers use protected system routes', async () => {
  await api.getBackupReplicaStatus()
  await api.configureBackupReplica('D:/copies')
  await api.disableBackupReplica()
  assert.deepEqual(requests.slice(-3).map(({ method, url }) => ({ method, url })), [
    { method: 'get', url: '/system/backup-replica-status' },
    { method: 'put', url: '/system/backup-replica' },
    { method: 'delete', url: '/system/backup-replica' },
  ])
})

test('Settings uses picker and exposes directory name only', async () => {
  const source = await readFile(new URL('../src/views/Settings.vue', import.meta.url), 'utf8')
  assert.match(source, /window\.sellhelp\?\.selectBackupDirectory/)
  assert.match(source, /replicaStatus\.directory_name/)
  assert.doesNotMatch(source, /replicaStatus\.directory\b/)
})
```

- [ ] **Step 2: Run RED test**

Run: `node --test frontend/tests/desktop-backup-ui.test.mjs frontend/tests/desktop-offsite-backup-ui.test.mjs`

Expected: API helpers and UI status do not exist.

- [ ] **Step 3: Implement controls and documentation**

```javascript
export const getBackupReplicaStatus = () => api.get('/system/backup-replica-status')
export const configureBackupReplica = directory => api.put('/system/backup-replica', null, { params: { directory } })
export const disableBackupReplica = () => api.delete('/system/backup-replica')

async function chooseBackupReplicaDirectory() {
  const directory = await window.sellhelp?.selectBackupDirectory?.()
  if (!directory) return
  await configureBackupReplica(directory)
  await loadBackups()
}
```

Load backup list, local status, and replica status in one `Promise.all`. Add an unframed status/control section to the existing backup tab that shows configuration, directory name, policy, last success, pending state, and safe errors. Hide picker controls outside Electron; preserve manual backup, download, restore, and delete. Document target selection, hourly retry, disabling without deletion, and use of a different physical disk.

- [ ] **Step 4: Run GREEN test and commit**

Run: `npm.cmd test`

Run: `npm.cmd run build`

Expected: suite and build pass, except recorded existing Sass/bundle warnings. Commit `feat: manage desktop offsite backup replicas` with Task 4 files.

### Task 5: Full Regression and Evidence

**Files:**
- Modify: `docs/superpowers/plans/2026-08-19-desktop-offsite-backups.md`

- [ ] **Step 1: Run final verification**

Run: `python -m pytest backend/tests -q`

Run: `npm.cmd --prefix desktop test`

Run: `npm.cmd test`

Run: `npm.cmd run build`

Expected: all suites and build pass.

- [ ] **Step 2: Review scope and record verified evidence**

Run: `git diff --check 046cc7f..HEAD`

Run: `git status --short`

Expected: no whitespace errors or generated output. Mark only executed checks, then commit `docs: record offsite backup verification` with this plan file only.
