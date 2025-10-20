@echo off
setlocal enableextensions

rem --- Текущая папка, где запущен бат ---
set "CUR=%CD%"

rem --- Используем расширенный путь \\?\ чтобы обойти спец. имя NUL ---
set "TARGET=\\?\%CUR%\nul"

echo [i] Папка: %CUR%
echo [i] Цель:  %TARGET%
echo.

rem --- Сначала пробуем удалить файл с именем "nul" ---
if exist "%TARGET%" (
  del /f /q "%TARGET%" >nul 2>&1
)

rem --- Если вдруг "nul" это каталог, удалим каталог рекурсивно ---
if exist "%TARGET%\*" (
  rd /s /q "%TARGET%" >nul 2>&1
)

rem --- Проверим, удалилось ли ---
if exist "%TARGET%" (
  echo [!] Не удалось удалить "nul". Попробуй запустить от администратора или закрыть процессы, держащие дескриптор.
  exit /b 1
) else (
  echo [+] "nul" в этой папке удален (если был).
  exit /b 0
)
