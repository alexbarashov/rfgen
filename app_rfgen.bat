@echo off
echo ====================================================
echo AIS GMSK Plot (Realtime SDR + File mode)
echo ====================================================

REM Переходим в папку проекта
cd /d "%~dp0"

REM Включаем DEBUG логирование для отладки нового формата
REM set BEACON_LOG=DEBUG

echo.
echo  Starting AIS GMSK plot...
python -m rfgen.ui_qt.app

echo.
echo ====================================================
echo App closed. Press any key to exit...
pause >nul
