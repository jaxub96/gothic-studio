@echo off
rem Launch Gothic Studio. Uses .venv if present, otherwise the system python.
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" studio.py
) else (
    python studio.py
)
pause
