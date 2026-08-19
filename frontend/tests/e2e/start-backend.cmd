@echo off
setlocal
if "%SELLHELP_E2E_BACKEND_PORT%"=="" set "SELLHELP_E2E_BACKEND_PORT=8005"
python -m alembic upgrade head
if errorlevel 1 exit /b 1
python -m uvicorn app.main:app --host 127.0.0.1 --port %SELLHELP_E2E_BACKEND_PORT%
