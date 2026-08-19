# Desktop Offsite Backup Design

## Goal

Protect the desktop application's locally retained SQLite backups from a
single-device failure. An owner can select one external or synchronised
directory, and the desktop application will maintain a verified copy of the
latest automatic backups there without relying on a paid cloud integration.

## Scope

- Available only in packaged Windows desktop mode and only to the owner role.
- Supports one owner-selected directory, including removable media, mapped
  network drives, and locally synchronised folders.
- Retains the existing local automatic-backup schedule: hourly checks, a new
  local SQLite copy every 24 hours, and fourteen local automatic copies.
- Replicates the newest completed local automatic backup to the configured
  directory and retains the newest fourteen automatic replica files there.
- Keeps manual backups, restore-protection copies, migration backups, and all
  non-SellHelp files untouched.

The feature does not implement cloud-provider APIs, credential storage,
multi-destination replication, database schema changes, or installer signing.

## Architecture

`DesktopOffsiteBackupService` is a separate service from the existing local
backup service. The local service remains the source of truth for creating
online SQLite copies. On every desktop scheduler tick, the scheduler first
runs the local due check, then asks the offsite service to synchronise the
newest valid local automatic backup when an offsite target is configured.

The service persists configuration and status in `SystemConfig`, using a new
JSON value that contains the configured directory, last successful replica,
and last failure. No migration is required. API responses expose only the
directory basename and status fields, never the full path.

Replica writes use a target-side temporary name, a SQLite readability check,
and an atomic replacement. A failed write removes its temporary file and
persists a short error type. Local backup creation, application startup, and
business requests continue even when the offsite target is unavailable. The
next hourly scheduler tick retries the newest local automatic backup.

## Desktop Integration

The Electron main process owns a fixed IPC handler that opens the native
directory picker. Its preload bridge exposes only that picker; the renderer
receives a selected path but never gains general filesystem access.

The owner Settings backup tab adds an offsite-replica section with:

- configured/not-configured state and selected directory name;
- a `Choose directory` action in desktop mode;
- a disable action that removes only configuration;
- last successful replica, pending state, and latest retryable error.

The browser build reports that the capability is unavailable. Non-owner roles
remain protected by the existing `/api/system` authorization boundary.

## API Contract

- `GET /api/system/backup-replica-status` returns desktop availability,
  configuration state, directory name, retention policy, last success, and
  last failure without a full filesystem path.
- `PUT /api/system/backup-replica` stores a selected absolute directory only
  after desktop-mode validation that it exists and is writable.
- `DELETE /api/system/backup-replica` disables future replication and keeps
  all existing local and external backup files.

All routes remain owner-only through the existing system router.

## Acceptance Criteria

- A valid configured target receives a readable SQLite copy of the newest
  automatic local backup and retains exactly fourteen automatic replicas.
- A missing or unwritable target leaves local backups intact, records a safe
  failure status, removes partial files, and retries on a later scheduler
  tick.
- Paths, filesystem errors, and renderer-supplied shell commands are not
  exposed through the UI or API.
- Browser mode never writes or configures an offsite target.
- Backend, frontend, desktop runtime, and production-build checks pass.
