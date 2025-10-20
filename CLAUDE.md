# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Communication Language

**IMPORTANT**: Always respond in **Russian language**. Generate commits, descriptions, and documentation in Russian unless explicitly requested otherwise.



## Обзор проекта

**rfgen** — это кроссплатформенный универсальный RF-генератор для генерации непрерывных RF-сигналов для тестирования и разработки. Проект находится на ранней стадии разработки (каркас/прототип).

Основные возможности:
- **Простые непрерывные сигналы**: Carrier/AM/FM/PM, тоны, свипы, шум
- **Тестовые битовые паттерны**: FF00h, F0F0h, 3333h, 5555h для отладки сигнальных трактов
- **Стандартизованные режимы**: PSK-406, AIS (тестовые шаблоны), DSC VHF, DSC HF, 121.5 AM (тон/свип)

Генератор формирует IQ-буферы и подаёт их в backend (HackRF или FileOut). Для работы в реальном времени backend работает в режиме loop или N-повторов с gap (нулевые сэмплы) внутри кадра для сохранения непрерывности.

## Команды разработки

### Запуск приложения

**Qt UI (PySide6):**
```bash
python -m rfgen.ui_qt.app
```

Или через удобный скрипт:
```bash
app_rfgen.bat
```

**CLI интерфейс:**
```bash
python -m rfgen.cli.rfgen_cli --fs 2000000 --mod FM --dev 5000 --pattern Tone --tone 1000 --outdir out --name test_frame
```

### Зависимости

Установка требований:
```bash
pip install -r rfgen/requirements.txt
```

Требования:
- Python 3.9+
- PySide6 (Qt UI)
- numpy<2

### Утилиты и скрипты

**Утилита HackRF:**
```bash
kill_hackrf.bat          # Остановить все процессы hackrf_transfer (graceful → force)
```

**Дополнительные скрипты:**
```bash
app_rfgen_gpt.bat        # Альтернативный вариант запуска с настройками
del_nul.bat              # Очистка служебных файлов
```

**Диагностика HackRF:**
```bash
hackrf_info              # Показать информацию о подключённых устройствах HackRF
```

## Архитектура

### Структура каталогов

```
rfgen/
  core/                 # Ядро генерации сигналов (модуляция, паттерны, wave_engine)
  standards/            # Протокольная логика (PSK-406, AIS, DSC, NAVTEX и т.д.)
  backends/             # Аппаратные выводы (HackRF, FileOut, Pluto)
  ui_qt/                # Qt приложение (PySide6)
    pages/              # UI страницы для каждого стандарта + служебные
    components/         # Общие виджеты
  cli/                  # CLI интерфейс
  utils/                # Утилиты (paths, profile_io, migrate)
  profiles/             # JSON профили (игнорируются в git)
  out/                  # Сгенерированные IQ-файлы (игнорируются в git)
  logs/                 # Логи работы backends (игнорируются в git)
  docs/                 # Документация и спецификации
  tests/                # Тесты
```

### Слоистая архитектура

**1. WaveEngine (core/wave_engine.py)**
- Точка входа: `build_iq(profile, frame_s)` - генерирует IQ-буфер из профиля
- Точка входа: `build_cw(profile, frame_s)` - генерирует константную несущую (CW)
- Принимает SignalSpec, ModulatorSpec, Schedule
- Склеивает источники (тон/паттерн/шум/сообщение) с модулятором (AM/FM/PM) в непрерывный IQ-поток
- Поддерживает плавные переходы (огибающие), контроль уровня, предотвращение клиппинга

**2. Модули модуляции (core/mod_*.py)**
- **mod_fm.py**: FM модуляция с девиацией (Hz), тон/свип/битовый драйвер
- **mod_pm.py**: Фазовая модуляция с фазовым индексом (rad), плавные фронты (заимствованы из логики PSK-406)
- **mod_am.py**: AM модуляция с глубиной (0..1), варианты A3E/DSB/SC

Функции в wave_engine.py:
- `generate_base_signal(kind, fs, dur_s, tone_hz)` - создаёт модулирующий сигнал
- `mod_none(fs, m)` - без модуляции (несущая)
- `mod_am(fs, m, depth)` - AM модуляция
- `mod_pm(fs, m, index_rad)` - PM модуляция
- `mod_fm(fs, m, deviation_hz)` - FM модуляция

**3. Паттерны (core/patterns.py)**
- Бесконечные битовые циклы: FF00 / F0F0 / 3333 / 5555 (с полем bitrate_bps)
- Tone (частота Hz), Sweep, Noise, ступеньки девиации (DEV-steps)

**4. Стандарты (standards/)**
- **psk406.py** (или **c406.py**): COSPAS-SARSAT 406 MHz
  - hex → биты → полубиты → плавные фазовые фронты → IQ
  - BPSK модуляция с FEC и интерливингом
- **ais.py**: Автоматическая идентификационная система
  - GMSK 9600 bps, BT≈0.4
  - Builder → scrambler → CRC → framer → GMSK mapper
  - Поддержка NMEA VDM import
- **dsc_vhf.py**, **dsc_hf.py**: Digital Selective Calling
  - VHF/HF диапазоны
  - Настроечные тоны/AFSK непрерывно, затем кадры сообщений
  - Builder → framer → (A)FSK/MSK mapper
- **navtex.py**: Навигационные телекс-сообщения
  - SITOR-B encode → FSK mapper
  - Baud=100, shift=170 Hz
- **am_121p5.py**: 121.5 MHz аварийная частота
  - AM тон/свип для поисково-спасательных операций

**5. Backends (backends/)**
- **HackRFTx (hackrf.py)**:
  - `run_loop(iq_path, fs_tx, center_hz, tx_gain_db)` - запускает hackrf_transfer в режиме loop
  - `is_running()` - проверяет, идёт ли передача
  - `stop()` - останавливает передачу
  - Использует исполняемый файл hackrf_transfer с режимом loop (флаг -R)
  - Обрабатывает цифровой сдвиг IF, пересемплирование, управление gain/PA
- **FileOutBackend (fileout.py)**: Экспорт cf32/sc8 для оффлайн-воспроизведения и регрессионного тестирования
- В будущем: Pluto/USRP через общий интерфейс TxBackend

**6. Утилиты (utils/)**
- **paths.py**: Централизованное управление путями
  - `pkg_root()` - корень пакета rfgen/
  - `profiles_dir()`, `out_dir()`, `logs_dir()` - создают папки при первом обращении
  - Все пути внутри пакета rfgen/, никаких ссылок на `parents[3]`
- **profile_io.py**: Работа с профилями
  - `PROFILE_SCHEMA_VERSION = 1` - версионирование схемы
  - `defaults()`, `validate_profile()`, `apply_defaults()` - валидация и дефолты
  - `load_json()`, `save_json()` - загрузка/сохранение
- **migrate.py**: Миграция старых профилей из корневых каталогов в rfgen/profiles/

**7. Профили**
- JSON файлы с: standard + параметры + расписание + устройство + метаданные
- Хранятся в `rfgen/profiles/` (игнорируются в git)
- Управление через страницу Profiles (загрузка, дублирование, переименование, удаление, импорт/экспорт)

**8. Телеметрия и метрики**
- Журналы операций (старт/стоп/ошибки) в `rfgen/logs/`
- Логи hackrf_transfer: CMD, PID, путь к IQ, stdout/stderr
- Метрики: RMS/peak/девиация (оценка), длительности, битрейт

### Формат профиля

Профили — это JSON-файлы, хранящиеся в `rfgen/profiles/`:

```json
{
  "schema": 1,
  "name": "AIS_FF00_FM_cont",
  "standard": "basic",
  "standard_params": {},
  "modulation": {
    "type": "FM",
    "deviation_hz": 5000,
    "pm_index": 1.0,
    "am_depth": 0.5
  },
  "pattern": {
    "type": "Tone",
    "tone_hz": 1000,
    "bitrate_bps": 9600
  },
  "schedule": {
    "mode": "loop",
    "gap_s": 0.0,
    "repeat": 1,
    "duration_s": 1.0
  },
  "device": {
    "backend": "hackrf",
    "fs_tx": 2000000,
    "tx_gain_db": 30,
    "pa": false,
    "target_hz": 162025000,
    "if_offset_hz": -25000,
    "freq_corr_hz": 0
  },
  "_meta": {
    "created_utc": "2025-10-20T12:00:00Z",
    "notes": "Тестовый профиль"
  }
}
```

**Типы стандартов**: `basic`, `ais`, `c406`, `dsc_vhf`, `dsc_hf`, `navtex`, `121`

**Типы модуляции**: `None`, `AM`, `FM`, `PM`

**Типы паттернов**: `Tone`, `Sweep`, `Noise`, `FF00`, `F0F0`, `3333`, `5555`

### Конечный автомат TX

```
Idle → Preparing (генерация/ресемплирование) → Armed → Transmitting (loop/N) → Stopping → Idle
```

Непрерывность обеспечивается:
- Режим loop: повтор одного и того же кадра
- N-повторы: вставка gap (нули) внутри кадра

### Страницы Qt UI

UI организован как sidebar с переключением между тематическими страницами:

1. **Basic** (`page_gen_basic.py`): Универсальная страница для простых сигналов
   - Непрерывные CW/AM/FM/PM сигналы
   - Тестовые паттерны: FF00, F0F0, 3333, 5555, Tone, Sweep, Noise
   - Управление устройством (backend, Fs TX, TX Gain, Target, IF offset)
   - Режим loop (непрерывная передача)
   - Start/Stop/Save Profile/Load Profile

2. **AIS** (`page_ais.py`): Генерация AIS-сигналов
   - GMSK 9600 bps, BT≈0.4
   - Channel A/B или ручная настройка частоты
   - NMEA VDM import
   - Тестовый режим (PRBS/паттерны)

3. **406 MHz** (`page_406.py`): COSPAS-SARSAT 406 МГц
   - BPSK модуляция
   - Beacon/Hex ID, тип сообщения
   - FEC/интерлив preset
   - ⚠️ По умолчанию fileout (юридические ограничения!)

4. **DSC VHF** (`page_dsc_vhf.py`): Digital Selective Calling VHF
   - Адресация/категория/поля из ITU-R
   - AFSK/FSK/MSK опции

5. **DSC HF** (`page_dsc_hf.py`): Digital Selective Calling HF
   - Аналогично DSC VHF для HF диапазона

6. **NAVTEX** (`page_navtex.py`): Навигационные телекс-сообщения
   - SITOR-B encode
   - Baud=100, shift=170 Hz
   - Ввод текста или загрузка из файла

7. **121.5 MHz** (`page_121.py`): Аварийная частота
   - CW/AM tone/sweep
   - Настройка глубины модуляции и скважности

8. **Profiles** (`page_profiles.py`): Менеджер профилей
   - Просмотр списка профилей из `rfgen/profiles/`
   - Load/Duplicate/Rename/Delete
   - Import/Export профилей
   - Предпросмотр JSON
   - События `profile_loaded(profile)` для интеграции с другими страницами

9. **Logs** (`page_logs.py`): Диагностика и логи
   - Просмотр логов из `rfgen/logs/`
   - Tail/Refresh, Open in Explorer
   - Kill all hackrf_transfer
   - Диагностика: версии ПО, PATH, наличие hackrf_transfer, запущенные процессы
   - Clear logs (с подтверждением)

## Важные принципы проектирования

### Режим STRICT_COMPAT

Проект следует строгой обратной совместимости:
- Никогда не ломать публичные API
- Новые функции добавляются через флаги
- HackRF backend воспроизводит текущие привычные параметры: LO/IF, цифровой сдвиг, repeat/gap, поведение loop
- Переиспользовать существующие имена полей UI (Target/IF/FreqCorr/TxGain/Fs_tx/Repeat/Gap)
- PSK-406: сохранять логику плавных фронтов, поддерживать ограничения front_samples

### Правила разработки

- **Минимальные PR**: Отдельные PR для отдельных страниц/UI-узлов/модулей ядра
- **Smoke-тесты**: Каждый PR должен быть привязан к простым smoke-тестам (открытие UI, сохранение профиля, генерация cf32)
- **Никаких breaking changes**: Поддерживать стабильность API на протяжении всей разработки
- **Централизация путей**: Все обращения к файловой системе только через `utils/paths.py`
- **Чистка артефактов**: Все профили/IQ/логи только в `rfgen/`, не в корне репозитория

### Поведение Start/Stop в UI

**Start:**
- Отключить кнопки Start/Save/Load
- Включить кнопку Stop
- Сформировать IQ-буфер, сохранить в `rfgen/out/`
- Запустить backend (HackRF или FileOut)
- Обновить статус: отобразить PID, center/fs, путь к логу
- Записать лог в `rfgen/logs/`

**Stop:**
- Вызвать `backend.stop()` (terminate → wait → kill)
- Логировать все шаги остановки
- После остановки вернуть кнопки в исходное состояние
- Обновить статус: "Stopped"

**Опция перед Start (настройки):**
- Kill stale hackrf_transfer процессы (`taskkill /IM hackrf_transfer.exe /F`)
- Полезно из-за известной проблемы с зомби-процессами на Windows

### Детали HackRF Backend

HackRF backend (`backends/hackrf.py`) оборачивает исполняемый файл `hackrf_transfer`:
- Использует subprocess для запуска hackrf_transfer с флагом -R (режим повтора/loop)
- IQ данные предварительно генерируются и сохраняются в файл
- Поддерживает Windows-специфичную обработку групп процессов для чистого завершения
- Параметры: центральная частота, частота дискретизации, TX gain, режим loop

### Поток генерации сигнала

1. Профиль определяет: тип паттерна, тип модуляции, параметры устройства
2. `wave_engine.build_iq()` генерирует baseband IQ-буфер:
   - Создаёт модулирующий сигнал (тон/свип/шум/паттерн)
   - Применяет модуляцию (AM/FM/PM или нет)
   - Масштабирует до безопасного уровня (≤0.8) для избежания клиппинга DAC
3. Backend (HackRF или FileOut) потребляет IQ-буфер
4. Для HackRF: IQ сохраняется в файл, hackrf_transfer запускается с режимом loop

## Текущий статус реализации

Это каркас/прототип. Реализовано:
- Базовая структура Qt UI с навигацией по страницам
- Базовая генерация сигналов: тон, свип, шум
- AM/FM/PM модуляция
- HackRF backend с режимом loop
- FileOut backend для оффлайн-тестирования
- Инфраструктура сохранения/загрузки профилей
- CLI интерфейс для быстрого тестирования

Ещё не реализовано (только заглушки/скелеты):
- Полная реализация PSK-406
- AIS GMSK (в процессе)
- Протоколы DSC (скелеты UI готовы)
- NAVTEX SITOR-B (скелет UI готов)
- Генерация битовых паттернов (FF00/F0F0/3333/5555)
- Продвинутая телеметрия/метрики

## Известные проблемы

См. файл `KNOWN_ISSUES.md` для полного списка. Основные:

**❌ HackRF Stop не работает (Windows)**
- Кнопка Stop в UI не останавливает передачу HackRF корректно
- Процесс `hackrf_transfer.exe` становится зомби
- Даже `taskkill /F` не может убить процесс
- **Workaround**: используйте `kill_hackrf.bat` для ручной остановки
- Если не помогает - требуется перезагрузка Windows
- После Start рекомендуется закрывать приложение полностью и перезапускать для нового Start

Возможные причины: Windows-специфичная проблема с процессами, HackRF driver держит ресурсы, file handle на устройство не освобождается.

TODO: протестировать на Linux, исследовать альтернативы subprocess, рассмотреть libhackrf API для Python.

## Общие паттерны

**Создание нового стандарта сигнала:**
1. Добавить модуль в `rfgen/standards/` (например, `new_standard.py`)
2. Реализовать функцию генерации, возвращающую IQ-буфер
3. Добавить новый тип стандарта в `utils/profile_io.py` (defaults, validation)
4. Создать новую страницу в `ui_qt/pages/page_new_standard.py`
5. Добавить страницу в `main_window.py` (импорт, инициализация, добавление в sidebar и stack)
6. Обновить WaveEngine для вызова стандарт-специфичного генератора (если нужно)

**Работа с путями:**
- ВСЕГДА использовать функции из `utils/paths.py`
- НИКОГДА не использовать `Path(__file__).resolve().parents[...]`
- Все артефакты (профили, IQ-файлы, логи) должны быть внутри `rfgen/`
- При первом обращении папки создаются автоматически

**Миграция старых профилей:**
Если в корне репозитория (`C:\work\rfgen\profiles\`) есть старые профили:
```python
from rfgen.utils.migrate import migrate_legacy_profiles
migrate_legacy_profiles()  # Перенесёт в rfgen/profiles/ без перезаписи
```

**Работа с профилями:**
```python
from rfgen.utils.profile_io import load_json, save_json, validate_profile, apply_defaults
from rfgen.utils.paths import profiles_dir

# Загрузка профиля
profile = load_json(profiles_dir() / "my_profile.json")

# Применение дефолтов и валидация
profile = apply_defaults(profile)
ok, msg = validate_profile(profile)

# Сохранение
save_json(profiles_dir() / "my_profile.json", profile)
```

**Тестирование генерации сигнала:**
1. Использовать CLI для генерации тестового файла: `python -m rfgen.cli.rfgen_cli --mod FM --pattern Tone --outdir out`
2. Проверить вывод в каталоге `out/`
3. Проверить с помощью внешних SDR-инструментов или воспроизведения на HackRF

**Добавление нового типа модуляции:**
1. Создать `mod_xxx.py` в `rfgen/core/`
2. Реализовать функцию модуляции: `mod_xxx(fs, m, **params) -> iq`
3. Добавить в `build_iq()` в `wave_engine.py`
4. Обновить UI-элементы управления для отображения новых параметров

## Приёмочные критерии для новых функций

При добавлении новой функциональности проверьте:

**Навигация и UI:**
- ✅ Все вкладки отображаются и открываются корректно
- ✅ Sidebar правильно переключает страницы
- ✅ Статусбар отображает актуальную информацию

**Пути и артефакты:**
- ✅ Все артефакты (профили, IQ, логи) создаются **строго** внутри `rfgen/`
- ✅ Нет использования `Path(__file__).resolve().parents[...]`
- ✅ Нет корневых папок `profiles/`, `out/` вне `rfgen/`

**Basic страница:**
- ✅ Start/Stop стабильно работают
- ✅ При IF=0: уровень в утилите `-inf dBFS` (ожидаемое поведение для DC)
- ✅ При IF≠0: уровень нормальный, тон на `target±IF`

**Profiles:**
- ✅ Save/Load работают из `rfgen/profiles/`
- ✅ Миграция отрабатывает для старых профилей
- ✅ Валидация профилей работает
- ✅ Превью JSON корректно отображается

**Logs:**
- ✅ Логи появляются в `rfgen/logs/`
- ✅ В логах видны: CMD, PID, строки `[stop] ... stopped, returncode=...`
- ✅ Tail/Refresh работают корректно

## Специфика Windows

Проект разрабатывается в первую очередь для Windows, учитывайте:

**Пути:**
- Используйте `Path` из `pathlib` для кроссплатформенности
- Не используйте прямые `/` или `\` в путях

**Процессы:**
- HackRF backend использует subprocess с особенностями Windows
- CREATE_NEW_PROCESS_GROUP для корректного управления процессами
- taskkill как fallback для убийства зомби-процессов

**Кодировки:**
- Логи в UTF-8 (с обработкой ошибок для совместимости)
- Переменная окружения `PYTHONIOENCODING=utf-8` может потребоваться

**Батники:**
- `.bat` файлы для удобного запуска
- `@echo off` и правильная обработка путей с пробелами
