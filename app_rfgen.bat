@echo off
echo ====================================================
echo RF gen
echo ====================================================

REM Переходим в папку проекта
cd /d "%~dp0"

REM Включаем DEBUG логирование для отладки нового формата
REM set BEACON_LOG=DEBUG

echo.
echo  Starting RF gen...
python -m rfgen.ui_qt.app

echo.
echo ====================================================
echo App closed. Press any key to exit...
pause >nul
