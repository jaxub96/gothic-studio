@echo off
rem
rem make-shortcut.bat - a "Gothic Studio" shortcut on the Desktop and in the Start
rem menu that runs the app from this source folder, like an exe: no console
rem window, the app's own icon, and every edit to the .py files picked up on the
rem next launch. No build needed.
rem
rem     cd gothic-studio
rem     make-shortcut.bat
rem
rem Or just double-click it. Sets up .venv first if it is missing. Run it again
rem if you move this folder, since the shortcut points at the old location.
rem
rem Nothing shows if the app fails to start (there is no console to print to);
rem run.bat runs the same thing with the error visible.
rem
setlocal
cd /d "%~dp0"

set "VENV=.venv"
set "PYW=%VENV%\Scripts\pythonw.exe"

rem --- 1. Virtual environment with the app's dependencies -------------------

if exist "%PYW%" goto :deps

echo ==^> Creating %VENV%
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
%BOOTPY% -m venv "%VENV%"
if errorlevel 1 goto :fail

:deps
"%VENV%\Scripts\python.exe" -c "import PyQt6, numpy" >nul 2>&1
if errorlevel 1 (
    echo ==^> Installing dependencies ^(a minute or so^)
    "%VENV%\Scripts\python.exe" -m pip install --quiet -r requirements.txt
    if errorlevel 1 goto :fail
)

rem --- 2. Shortcuts ----------------------------------------------------------
rem
rem GetFolderPath, not %USERPROFILE%\Desktop: OneDrive often moves the Desktop.

echo ==^> Creating shortcuts
set "GS_ROOT=%CD%"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = $env:GS_ROOT; $shell = New-Object -ComObject WScript.Shell;" ^
  "foreach ($dir in [Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs')) {" ^
  "  $lnk = $shell.CreateShortcut((Join-Path $dir 'Gothic Studio.lnk'));" ^
  "  $lnk.TargetPath = Join-Path $root '.venv\Scripts\pythonw.exe';" ^
  "  $lnk.Arguments = 'studio.py';" ^
  "  $lnk.WorkingDirectory = $root;" ^
  "  $lnk.IconLocation = (Join-Path $root 'assets\icon.ico') + ',0';" ^
  "  $lnk.Description = 'Gothic Studio (from source)';" ^
  "  $lnk.Save(); Write-Host ('   ' + $lnk.FullName) }"
if errorlevel 1 goto :fail

echo.
echo Done. Start Gothic Studio from the Desktop or the Start menu; pin it to the
echo taskbar from there if you like.
endlocal
exit /b 0

:fail
echo.
echo Failed - see the message above.
pause
endlocal
exit /b 1
