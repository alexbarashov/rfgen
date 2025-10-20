@echo off
REM ===== Simple launcher for rfgen UI (Python 3.9) =====
cd /d %~dp0

REM 1) Create venv if missing
if not exist ".venv\Scripts\python.exe" (
  py -3.9 -m venv .venv
  if errorlevel 1 (
    echo [rfgen] Failed to create venv
    pause
    exit /b 1
  )
)

REM 2) Activate venv
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
  echo [rfgen] Failed to activate venv
  pause
  exit /b 1
)

REM 3) Ensure deps (pin numpy<2 to avoid ABI issues)
python -m pip install --upgrade pip >nul
pip install "numpy<2,>=1.26.4" PySide6 >nul
if errorlevel 1 (
  echo [rfgen] Failed to install dependencies (numpy<2, PySide6)
  pause
  exit /b 1
)

REM 4) Run UI
python -m rfgen.ui_qt.app
set EXITCODE=%ERRORLEVEL%

echo.
echo [rfgen] Exit code: %EXITCODE%
pause
exit /b %EXITCODE%
