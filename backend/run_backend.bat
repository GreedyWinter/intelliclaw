@echo off
setlocal
set ROOT=%~dp0..
set PYTHON=%~dp0.venv\Scripts\python.exe

if not exist "%PYTHON%" (
  echo Backend virtualenv Python not found at %PYTHON%
  exit /b 1
)

cd /d "%ROOT%"
"%PYTHON%" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
