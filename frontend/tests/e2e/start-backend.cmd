@echo off
python -m alembic upgrade head
if errorlevel 1 exit /b 1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8005
