@echo off
rem Launch Gothic Studio from source. Uses .venv if present, otherwise the system python.
rem Extra arguments pass through; "run.bat --dev" runs without a Gothic II install.
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" studio.py %*
) else (
    python studio.py %*
)
if errorlevel 1 pause
