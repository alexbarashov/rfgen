@echo off
echo Stopping HackRF transfer processes...

REM Сначала пробуем graceful shutdown
taskkill /IM hackrf_transfer.exe /T 2>nul

REM Ждём 2 секунды
timeout /t 2 /nobreak >nul 2>nul

REM Проверяем, остались ли процессы
tasklist /FI "IMAGENAME eq hackrf_transfer.exe" 2>nul | find /I "hackrf_transfer.exe" >nul

if %ERRORLEVEL% EQU 0 (
    echo Processes still running, force killing...
    taskkill /IM hackrf_transfer.exe /F /T
) else (
    echo All processes stopped gracefully.
)

echo Done.
