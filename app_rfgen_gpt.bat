@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d %~dp0

rem --- venv ---
if not exist ".venv\Scripts\python.exe" (
  py -3.9 -m venv .venv || (echo [rfgen] venv failed & exit /b 1)
)
call ".venv\Scripts\activate.bat" || (echo [rfgen] activate failed & exit /b 1)

rem --- изоляция от системных пакетов / PothosSDR ---
set PYTHONNOUSERSITE=1
set PYTHONPATH=
set QT_PLUGIN_PATH=
set QML2_IMPORT_PATH=

rem --- зависимости (numpy<2 чтобы не ловить краш) ---
python -m pip install --upgrade pip
pip install "numpy<2,>=1.26.4" PySide6 || (echo [rfgen] deps failed & exit /b 1)

rem --- проверка структуры ---
if not exist "rfgen\__init__.py" (
  echo [rfgen] ERROR: запусти этот батник из папки, где лежит каталог ^'rfgen^'
  exit /b 1
)

rem --- изолированный запуск (чистим sys.path от чужих путей) ---
python - <<PY
import os, sys
VENV=sys.prefix; CWD=os.getcwd()
def keep(p):
    if not p: return True
    P=os.path.abspath(p)
    return P.startswith(os.path.abspath(VENV)) or P.startswith(os.path.abspath(CWD))
sys.path=[p for p in sys.path if keep(p)]
for v in ("PYTHONPATH","QT_PLUGIN_PATH","QML2_IMPORT_PATH"):
    os.environ.pop(v, None)
from rfgen.ui_qt.app import main
main()
PY
pause >nul