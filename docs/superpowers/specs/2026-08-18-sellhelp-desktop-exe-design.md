# SellHelp Windows Desktop Release Design

## Scope

The first desktop release targets Windows 10/11 x64. It installs as an NSIS
EXE, runs without Python, Node.js, or an internet connection after
installation, and keeps all operator data outside the installation directory.
Automatic updates and Authenticode signing are excluded because they require
release hosting and a code-signing certificate that are not present in this
repository.

## Architecture

Electron is the desktop shell because the existing UI is Vue and the
application already has a Node build workflow. Electron starts a bundled
FastAPI executable on the loopback interface, waits for `/api/health`, and
loads the same local HTTP origin in one BrowserWindow. The backend serves the
production `frontend/dist` files and API routes, so the existing relative
`/api` client remains valid. The window uses context isolation and does not
expose Node integration to the renderer.

The backend receives its data directory and runtime port as explicit command
line arguments. It binds only to `127.0.0.1`, has no reload mode, and produces
a machine-readable readiness line. Electron owns the child lifecycle, stops
it when the app exits, and shows a useful launch failure view if readiness is
not reached.

## Persistent Data And Startup

All mutable files live below `%LOCALAPPDATA%\\SellHelp`:

- `data\\sellhelp.db`: SQLite business database.
- `backups`: manual and pre-restore backups.
- `logs`: rotating application logs.
- `config`: protected local configuration, including a generated JWT secret.

The backend creates the data directory on first launch. Before schema work it
creates a timestamped safety backup for an existing database, then applies a
deterministic Alembic path: new database upgrades from base; legacy database
without an Alembic marker is stamped at the legacy baseline and upgraded; an
existing marker upgrades to head. Seed business data is never added during an
upgrade.

The JWT secret is generated with Python `secrets` only when no secret was
provided, then encrypted with Windows DPAPI before it is written to the local
configuration file. Packaged desktop mode uses the generated secret;
non-desktop deployments retain the existing requirement that a production
environment provide a 32-character secret before multi-user mode is enabled.

## Backup, Export, And Diagnostics

Backup and restore use the active SQLite database location rather than the
application source location. Backup files are created through SQLite's backup
API. A restore creates a pre-restore backup, disposes active database
connections, restores atomically, and tells the desktop shell to restart the
local backend.

The Electron main process handles downloads and save locations. Existing
browser downloads, print calls, and report exports must work from the packaged
window. Backend logs rotate in the data directory and startup failures include
the path to the diagnostic log.

## Build And Installer

`frontend` builds with Vite. PyInstaller packages the backend runtime,
Alembic migrations, and frontend build assets. Electron Builder packages the
frontend shell and backend executable into an NSIS installer with product
version, icon, uninstall entry, single-instance behavior, and preservation of
the user data directory on uninstall.

Backend dependencies are pinned for repeatable release builds. The installer
does not execute pip, npm, or development servers on the customer machine.

## Acceptance Criteria

1. A clean Windows machine installs and starts the EXE without Python, Node,
   or network access.
2. The packaged window displays the Vue application and all existing `/api`
   calls succeed through the local backend.
3. Closing the application stops its backend; a second launch focuses the
   existing window.
4. Data survives restart, application upgrade, and uninstall/reinstall.
5. Database migration, backup, restore, PDF/XLSX export, and print work from
   the installed application.
6. The backend is not reachable from non-loopback network interfaces.
7. Launch failure, port conflict, missing data directory permission, and a
   malformed database result in actionable diagnostics rather than a blank
   window.

## Deliberate First-Release Limits

- Windows x64 only.
- Offline local deployment only; no LAN server mode.
- No automatic update service.
- Installer is unsigned until a signing certificate is supplied.
