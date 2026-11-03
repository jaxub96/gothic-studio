@echo off
rem
rem build-windows.bat - one command from a fresh checkout to dist\GothicStudio.exe
rem
rem     cd gothic-studio
rem     build-windows.bat
rem
rem Or just double-click it. Safe to re-run: the venv is reused and packages
rem are only installed when missing. The Mac equivalent is build-macos.sh.
rem
setlocal
cd /d "%~dp0"

set "VENV=.venv"
set "PY=%VENV%\Scripts\python.exe"

rem --- 1. Python -----------------------------------------------------------

echo.
echo ==^> Checking Python

rem The py launcher is the reliable way to find a real install; plain "python"
rem on a clean Windows is a Store stub that does nothing useful.
set "BOOTPY="
py -3 --version >nul 2>&1 && set "BOOTPY=py -3"
if not defined BOOTPY (
    python --version >nul 2>&1 && set "BOOTPY=python"
)
if not defined BOOTPY (
    echo error: no Python found. Install it from https://www.python.org/downloads/
    echo        and tick "Add python.exe to PATH".
    goto :fail
)

%BOOTPY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo error: Python 3.10 or newer is required.
    %BOOTPY% --version
    goto :fail
)
for /f "delims=" %%v in ('%BOOTPY% -c "import platform;print(platform.python_version(), platform.machine())"') do echo python   %%v

rem --- 2. Virtual environment ----------------------------------------------

echo.
if exist "%PY%" (
    echo ==^> Reusing %VENV%
) else (
    echo ==^> Creating %VENV%
    %BOOTPY% -m venv "%VENV%"
    if errorlevel 1 goto :fail
)

rem --- 3. Dependencies -----------------------------------------------------

echo.
"%PY%" -c "import PyQt6, numpy, PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo ==^> Installing dependencies ^(a minute or so^)
    "%PY%" -m pip install --upgrade --quiet pip
    "%PY%" -m pip install --quiet -r requirements.txt
    if errorlevel 1 goto :fail
    "%PY%" -m pip install --quiet pyinstaller
    if errorlevel 1 goto :fail
) else (
    echo ==^> Dependencies already installed
)
"%PY%" -c "import PyQt6.QtCore as c; print('PyQt6   ', c.QT_VERSION_STR)"

rem --- 4. Smoke test -------------------------------------------------------
rem
rem Run from source before freezing: a failure here is far easier to read than
rem the same failure inside the exe. Not finding the mod is fine at this point,
rem so this must not be fatal.

echo.
echo ==^> Checking the source runs
"%PY%" studio.py --check
if errorlevel 1 (
    echo warning: no Gothic II found yet. Fine - the app asks on first launch.
)

rem --- 5. Build ------------------------------------------------------------

echo.
echo ==^> Building
"%PY%" build_exe.py
if errorlevel 1 (
    echo.
    echo Build failed. If it says the exe is running, close Gothic Studio first.
    goto :fail
)

echo.
echo ==^> Done
echo   %CD%\dist\GothicStudio.exe
echo.
echo Sending it to someone else? They get a SmartScreen warning on first run -
echo tell them to click "More info" then "Run anyway".
endlocal
exit /b 0

:fail
echo.
endlocal
exit /b 1
