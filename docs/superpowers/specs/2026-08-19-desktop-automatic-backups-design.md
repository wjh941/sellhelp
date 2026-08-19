# Desktop Automatic Backups Design

## Scope

This iteration adds no-cost, local automatic SQLite backups to the Windows
desktop application. It keeps the existing manual backup, download, restore,
and migration-protection workflows unchanged. It does not add cloud storage,
Windows Task Scheduler integration, a database migration, a new dependency,
or any change to browser deployments.

## Goals

- Create a safe local backup at least once every 24 hours while the desktop
  application is running.
- Retain the newest 14 automatic backups without deleting a manual backup or
  a pre-restore/pre-migration protection backup.
- Make the automatic-backup state visible in the existing Settings backup tab.
- Record a useful local failure state without delaying application startup or
  interrupting business operations.

## Alternatives Considered

1. Keep manual backups only. This is zero work but still depends on the user
   remembering to run a backup.
2. Run a desktop-only background due-checker. It checks on startup and then
   periodically while the app is open, performs a SQLite online backup when
   the last successful automatic backup is at least 24 hours old, and requires
   no extra Windows permissions. This is the selected approach.
3. Register a Windows Task Scheduler task. It could run while SellHelp is
   closed, but adds installation permissions, upgrade/cleanup complexity, and
   opaque failures. It is intentionally deferred.

## Architecture

### Desktop backup service

A focused desktop backup service owns the policy and file operations:

- It is constructed with the active SQLite database path, backup directory,
  session factory, and clock so its due calculation and retention behavior are
  directly testable.
- A successful automatic backup uses the existing SQLite backup API rather
  than copying a live database file.
- Automatic files use a dedicated `sellhelp_auto_` filename prefix. The system
  backup filename validation and listing accept that prefix alongside the
  existing manual and pre-restore names.
- After a successful write, the service removes only automatic files older
  than the 14 newest automatic copies. Manual backups and protection backups
  are never candidates for this cleanup.
- State is stored as JSON in the existing `SystemConfig` table under a
  dedicated automatic-backup key. It includes the most recent successful
  timestamp, filename, and byte count, plus the most recent failure timestamp
  and short error type. It does not store credentials or absolute file paths.

### Scheduling and lifecycle

The FastAPI lifespan starts the service only when `SELLHELP_DESKTOP_MODE=1`.
The desktop scheduler submits an initial due-check in the background, then
checks hourly. A check writes a backup only when 24 hours have elapsed since
the last successful automatic backup. This catches up after an application was
closed during the normal interval while avoiding a startup-blocking database
copy.

The lifespan shutdown stops the desktop backup scheduler. Browser and network
server modes neither start the scheduler nor expose the desktop-only automatic
state as enabled.

### Status API and Settings

`GET /api/system/backup-status` returns a small status object suitable for the
existing Settings backup tab:

- whether automatic desktop backup is enabled;
- the fixed 24-hour interval and 14-file retention policy;
- the latest successful automatic backup, when present;
- the latest recorded automatic failure, when present; and
- whether another backup is currently due.

The existing Settings backup tab loads this state together with the backup
list. It presents the enabled state, last success, retention count, and a
visible warning for the last failure. Existing manual backup, download,
restore, and delete controls remain where they are and retain their current
behavior.

## Error Handling

- A backup failure is caught by the scheduled job, written to the existing
  desktop log, and persisted as status. The job never takes down the backend
  or prevents a later retry.
- A partially created automatic file is removed when the SQLite backup API
  reports an error. Retention runs only after a complete, successful backup.
- A non-file SQLite URL is reported as an unavailable automatic-backup state;
  this preserves the existing explicit error behavior for manual backup and
  restore endpoints.
- Filename validation stays restrictive. The new automatic prefix is accepted
  only with the project timestamp format, so backup download, restore, and
  deletion cannot escape the active backup directory.

## Test Strategy

Backend tests will cover:

1. An overdue file-based SQLite database produces a readable automatic backup
   containing the source data and records a success state.
2. A recent success skips the copy; an overdue or failed prior run is retried.
3. Retention leaves exactly 14 automatic files and preserves manual and
   protection backups.
4. A write failure removes its partial file, records failure state, and lets a
   future run proceed.
5. The scheduler starts and stops only in desktop mode, without blocking
   application initialization.
6. The status endpoint exposes policy and status without an absolute data
   path, and the existing filename safety tests cover the new valid prefix.

Frontend contract tests will verify that the Settings view requests the new
status endpoint and renders the automatic status beside the existing backup
list. The full backend suite, frontend unit suite, desktop runtime tests, and
frontend production build remain release gates.

## Acceptance Criteria

1. A running desktop SellHelp instance creates an automatic SQLite backup at
   most one hour after startup when it has no successful automatic backup in
   the preceding 24 hours.
2. Automatic backups remain under `%LOCALAPPDATA%\\SellHelp\\backups` for the
   packaged application and use the configured database parent for supported
   development/test database URLs.
3. At most 14 automatic backups remain after each successful automatic run;
   manual, pre-restore, and pre-migration backups are not removed.
4. Settings accurately shows enabled state, last success, retention policy,
   and the latest automatic failure.
5. A failed automatic backup leaves the application available, is logged,
   appears in status, and is retried later.
6. All current manual backup and restore behavior, authorization, and
   filename/path safety protections continue to pass their existing tests.
