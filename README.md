# Sellhelp

Sellhelp is a local inventory and trade-management application with a FastAPI backend and Vue frontend.

## Prerequisites

- Python 3.11
- Node.js 18 or later

## Clean-clone setup

From the repository root, install the backend and frontend dependencies:

```powershell
pip install -r backend/requirements.txt
npm ci --prefix frontend
```

On Windows, run `start.bat` to initialize the local database and start both services. Open the frontend at http://localhost:8080 and the backend API documentation at http://localhost:8000/docs.

## Configuration

`SELLHELP_DATABASE_URL` overrides the default SQLite database connection. For example:

```powershell
$env:SELLHELP_DATABASE_URL = "sqlite:///C:/data/sellhelp.db"
```

`SELLHELP_ALLOWED_ORIGINS` is a comma-separated list of browser origins allowed by CORS. It defaults to `http://localhost:8080`:

```powershell
$env:SELLHELP_ALLOWED_ORIGINS = "http://localhost:8080,http://example.local"
```

## Verification

Run backend tests:

```powershell
Set-Location backend
python -m pytest -q
```

Build the frontend:

```powershell
Set-Location frontend
npm.cmd run build
```

## Backup and recovery

Database backups created by the application are stored under `backend/backup`. The system also creates a pre-restore backup there before a database restore.
