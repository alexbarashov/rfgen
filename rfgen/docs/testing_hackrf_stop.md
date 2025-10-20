# Тестирование остановки HackRF передачи

## Проблема
`hackrf_transfer` на Windows не останавливается через обычный `terminate()`. Нужно использовать `CTRL_BREAK_EVENT`.

## Решение
Реализована трёхступенчатая остановка процесса:

1. **CTRL_BREAK_EVENT** (только Windows) - hackrf_transfer обрабатывает этот сигнал для graceful shutdown
2. **terminate()** - если CTRL_BREAK не сработал
3. **kill()** - force kill если ничего не помогло

## Как протестировать

### Запуск передачи

1. Откройте приложение:
   ```bash
   python -m rfgen.ui_qt.app
   ```

2. Перейдите на страницу **Quick TX**

3. Настройте параметры:
   - Backend: hackrf
   - Target: любая частота (например, 162025000)
   - Modulation: FM
   - Pattern: Tone

4. Нажмите **Start TX**

5. Проверьте статус:
   - Должно появиться сообщение: `HackRF TX running (PID XXXXX). Log: hackrf_YYYYMMDD_HHMMSS.log`
   - Кнопки Start/Save/Load должны быть отключены
   - Кнопка Stop должна быть активна

### Остановка передачи

1. Нажмите **Stop**

2. Ожидаемый результат:
   - Передача останавливается в течение 2-3 секунд
   - Статус: `HackRF TX stopped.`
   - Кнопки Start/Save/Load снова активны
   - Кнопка Stop отключена

3. Проверьте, что процесс остановлен:
   ```bash
   tasklist | findstr hackrf_transfer
   ```
   Результат должен быть пустым (процесс не найден)

### Проверка логов

Логи находятся в `rfgen/logs/hackrf_YYYYMMDD_HHMMSS.log`

**Ожидаемое содержимое при остановке:**

```
[stop] stopping PID 12345
[stop] sending CTRL_BREAK_EVENT to PID 12345
[stop] stopped, returncode=0
```

Или, если CTRL_BREAK не сработал:

```
[stop] stopping PID 12345
[stop] sending CTRL_BREAK_EVENT to PID 12345
[stop] still running, sending terminate
[stop] stopped, returncode=1
```

Или, в крайнем случае:

```
[stop] stopping PID 12345
[stop] sending CTRL_BREAK_EVENT to PID 12345
[stop] still running, sending terminate
[stop] still running → kill()
[stop] stopped, returncode=-1
```

### Проверка повторного запуска

После остановки:

1. Сразу нажмите **Start TX** снова
2. Должна запуститься новая передача без ошибок
3. Не должно быть сообщений "HackRF already running"

## Альтернативный способ остановки

Если кнопка Stop не работает, используйте скрипт:

```bash
kill_hackrf.bat
```

Скрипт выполняет:
1. Graceful shutdown через `taskkill /IM hackrf_transfer.exe /T`
2. Ожидание 2 секунды
3. Force kill если процесс ещё работает: `taskkill /F`

## Диагностика проблем

### Stop не останавливает процесс

1. **Проверьте лог** в `rfgen/logs/`:
   - Нет строк `[stop]` → кнопка Stop не подключена к обработчику
   - Есть `[stop]`, но нет `stopped` → процесс завис, проверьте права

2. **Проверьте процессы вручную**:
   ```bash
   tasklist /FI "IMAGENAME eq hackrf_transfer.exe"
   ```

3. **Убейте вручную**:
   ```bash
   taskkill /IM hackrf_transfer.exe /F /T
   ```

### Множественные процессы

Если `tasklist` показывает несколько `hackrf_transfer.exe`:

1. Используйте `kill_hackrf.bat` для очистки всех процессов
2. Проверьте, что в коде нет множественных запусков
3. Убедитесь, что старые процессы правильно останавливаются

### CTRL_BREAK_EVENT не работает

Если в логе есть ошибки отправки CTRL_BREAK_EVENT:

1. Проверьте, что процесс создан с `CREATE_NEW_PROCESS_GROUP`
2. Убедитесь, что у процесса Python есть права на отправку сигналов
3. Проверьте версию hackrf_transfer (должна поддерживать CTRL_BREAK)

## Технические детали

### Почему CTRL_BREAK_EVENT?

На Windows:
- `CTRL_C_EVENT` не работает для subprocess (отправляется всем процессам консоли)
- `terminate()` может быть слишком грубым
- `hackrf_transfer` специально обрабатывает `CTRL_BREAK_EVENT` для graceful shutdown

### Последовательность остановки

```python
# 1. CTRL_BREAK (только Windows, 2 сек timeout)
os.kill(pid, signal.CTRL_BREAK_EVENT)
wait(2.0)

# 2. terminate (если ещё работает, 1 сек timeout)
proc.terminate()
wait(1.0)

# 3. kill (force, если всё ещё работает)
proc.kill()
```

## Критерии успешного теста

- ✅ При Start кнопки переключаются корректно
- ✅ Лог создаётся с CMD, PID, путём к IQ
- ✅ При Stop в логе есть `[stop] ...` сообщения
- ✅ Процесс исчезает из `tasklist` в течение 2-3 секунд
- ✅ Повторный Start работает сразу после Stop
- ✅ Нет зависших процессов после закрытия UI
