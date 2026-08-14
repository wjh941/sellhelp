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

On Windows, run `start.bat` to initialize the local database and start both services. Open the frontend at http://localhost:8080 and the backend API documentation at http://localhost:8001/docs.

## Configuration

`SELLHELP_DATABASE_URL` overrides the default SQLite database connection. For example:

```powershell
$env:SELLHELP_DATABASE_URL = "sqlite:///C:/data/sellhelp.db"
```

`SELLHELP_ALLOWED_ORIGINS` is a comma-separated list of browser origins allowed by CORS. It defaults to `http://localhost:8080`:

```powershell
$env:SELLHELP_ALLOWED_ORIGINS = "http://localhost:8080,http://example.local"
```

### External market sync

Configure `ANYSEARCH_API_KEY` only in the backend server environment, then restart the backend for the change to take effect. Do not put this value in the browser, frontend build, or source control.

```powershell
$env:ANYSEARCH_API_KEY = "your-server-side-key"
```

By default, external market data syncs daily at `02:00` in the `Asia/Shanghai` timezone. The schedule can be changed in Settings. Network quotes are always pending review: they affect local market prices and pricing calculations only after an operator manually confirms them.

The sync uses public price-monitoring information from the National Development and Reform Commission, public information from the National Food and Strategic Reserves Administration, and public retail search results. External content can be delayed, incomplete, or promotional, so operators must verify the source and retail context before accepting a quote.

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
