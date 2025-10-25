# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Communication Language

**IMPORTANT**: Always respond in **Russian language**. Generate commits, descriptions, and documentation in Russian unless explicitly requested otherwise.

## Быстрая справка

**Основные команды:**
```bash
# Запуск UI
python -m rfgen.ui_qt.app
app_rfgen.bat

# CLI генерация
python -m rfgen.cli.rfgen_cli --mod FM --pattern Tone --outdir out

# Диагностика HackRF
hackrf_info
kill_hackrf.bat
```

**Ключевые файлы:**
- `rfgen/utils/paths.py` - ВСЕ пути только через эту утилиту
- `rfgen/utils/profile_io.py` - валидация и работа с профилями
- `rfgen/utils/cf32_naming.py` - конвенция именования CF32 файлов
- `rfgen/core/wave_engine.py` - генерация базовых сигналов
- `rfgen/backends/hackrf.py` - HackRF backend

**Важные принципы:**
- Никогда не ломать обратную совместимость
- Все артефакты строго в `rfgen/` (profiles, out, logs)
- Автосохранение: остановить в начале `_apply_profile_to_form()`, запустить после
- CF32 файлы: использовать конвенцию `iq_<FSk>_<name>.cf32`

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
  utils/                # Утилиты (paths, profile_io, migrate, cf32_naming)
  profiles/             # JSON профили (игнорируются в git)
  out/                  # Сгенерированные IQ-файлы (игнорируются в git)
  logs/                 # Логи работы backends (игнорируются в git)
  docs/                 # Документация и спецификации
    implementation/     # Детальная документация реализации каждого стандарта
    task/               # Технические задания и заметки
  tests/                # Тесты (pytest)
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
- **psk406.py**: COSPAS-SARSAT 406 MHz
  - hex → биты → полубиты → плавные фазовые фронты → IQ
  - BPSK модуляция, 400 bps
  - Два режима: Direct HEX (реализовано) и Message Builder (TODO: FEC/интерлив)
- **ais.py**: Автоматическая идентификационная система
  - GMSK 9600 bps, BT≈0.4
  - Builder → scrambler → CRC → framer → GMSK mapper
  - Поддержка NMEA VDM import
  - **Важные детали генерации:**
    - Warm-up паддинг фильтра (12-24 символа guard "единиц" перед преамбулой)
    - Guard symbols после кадра (предотвращает скачки к 0 Hz)
    - Crossfade между шумом и несущей, сообщением и шумом
    - Модуляционный индекс h = 2·Δf/Rs (обычно Δf=2400 Hz → h=0.5)
    - Параметры настраиваются через `standard_params`: `deviation_hz`, `xfade_ms`, `pre_guard_ones_symbols`, etc.
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
  - Валидация модуляций: `None`, `AM`, `FM`, `PM`, `BPSK`, `GMSK`, `FSK`
  - Валидация паттернов: `Tone`, `Sweep`, `Noise`, `FF00`, `F0F0`, `3333`, `5555`, `406`, `121`, `AIS`, `DSC_VHF`, `DSC_HF`, `NAVTEX`
- **migrate.py**: Миграция старых профилей из корневых каталогов в rfgen/profiles/
- **cf32_naming.py**: Конвенция именования CF32 файлов
  - `parse_fs_from_filename()` - извлекает Fs из имени файла (например, `iq_1024_ais.cf32` → 1024000 Hz)
  - `generate_cf32_name()` - генерирует имя по конвенции `iq_<FSk>_<name>.cf32`
  - `sanitize_custom_name()` - очищает имя от недопустимых символов
  - Fallback: если Fs не определён → 1024000 Hz
  - Idempotency: повторная генерация не дублирует FSk в имени

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

**Типы модуляции**:
- Базовые: `None`, `AM`, `FM`, `PM`
- Стандарты: `BPSK`, `GMSK`, `FSK`

**Типы паттернов**:
- Базовые: `Tone`, `Sweep`, `Noise`, `FF00`, `F0F0`, `3333`, `5555`
- Стандарты: `406`, `121`, `AIS`, `DSC_VHF`, `DSC_HF`, `NAVTEX`

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
   - BPSK модуляция, 400 bps
   - **Два режима ввода:**
     - **Direct HEX** (по умолчанию): прямой ввод HEX сообщения
     - **Message Builder**: генерация из Beacon ID/Lat/Lon (UI готов, генератор TODO)
   - Настройки фазы, несущей, плавных фронтов
   - FEC/интерлив (UI готов, кодирование TODO)
   - ⚠️ По умолчанию fileout (юридические ограничения!)
   - Автосохранение в `default.json`

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
  - Для CF32: использовать конвенцию `iq_<FSk>_<name>.cf32` (см. `utils/cf32_naming.py`)
  - Для SC8: использовать формат `<name>.sc8`
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

**Автосохранение профилей:**
- Страницы автоматически сохраняют текущие настройки в `default.json`
- При изменении виджетов срабатывает таймер (500ms debounce)
- При загрузке профиля автосохранение временно отключается, чтобы избежать перезаписи

### Детали HackRF Backend

HackRF backend (`backends/hackrf.py`) оборачивает исполняемый файл `hackrf_transfer`:
- Использует subprocess для запуска hackrf_transfer с флагом -R (режим повтора/loop)
- IQ данные предварительно генерируются и сохраняются в файл
- Поддерживает Windows-специфичную обработку групп процессов для чистого завершения
- Параметры: центральная частота, частота дискретизации, TX gain, режим loop

### Поток генерации сигнала

1. Профиль определяет: тип паттерна, тип модуляции, параметры устройства
2. Генерация baseband IQ:
   - **Для Basic**: `wave_engine.build_iq()` - тон/свип/шум/паттерн + AM/FM/PM
   - **Для стандартов**: специфичный генератор (например, `build_psk406()` для 406 MHz)
   - Масштабирование до безопасного уровня (≤0.8) для избежания клиппинга DAC
3. Пересемплирование (если baseband Fs ≠ TX Fs):
   - `core/resample.py`: `resample_iq(iq_in, fs_in, fs_out)`
   - Использует scipy.signal.resample_poly для качественного ресемплирования
4. Цифровой IF сдвиг (если IF offset ≠ 0):
   - `backends/hackrf.py`: `_apply_if_shift(iq, if_offset_hz, fs_tx)`
   - Умножение на `exp(j*2π*f_IF*t)` для сдвига в частотной области
5. Backend (HackRF или FileOut) потребляет IQ-буфер:
   - **FileOut**: сохраняет CF32/SC8 файл с конвенцией именования
   - **HackRF**: сохраняет временный файл, запускает hackrf_transfer с режимом loop/N-повторов

## Текущий статус реализации

### ✅ Реализовано:
- Базовая структура Qt UI с навигацией по страницам
- Базовая генерация сигналов: тон, свип, шум
- AM/FM/PM модуляция
- HackRF backend с режимом loop и N-повторов
- FileOut backend для оффлайн-тестирования (CF32/SC8)
- Инфраструктура сохранения/загрузки профилей с автосохранением
- CLI интерфейс для быстрого тестирования
- **PSK-406**: Базовая генерация BPSK с Direct HEX режимом
- **AIS**: Полная реализация GMSK 9600 bps с NMEA VDM import, guard sequences, crossfade
- **DSC VHF**: Полная реализация с phasing tones и message frames
- **DSC HF**: Полная реализация для HF диапазона
- **NAVTEX**: Полная реализация SITOR-B на 518/490/4209.5 кГц
- **121.5 MHz**: AM tone/sweep для аварийной частоты
- **CF32 Naming Convention**: Стандартизованное именование файлов `iq_<FSk>_<name>.cf32`
- **Resample**: Пересемплирование между baseband и TX частотой
- **IF Offset**: Цифровой сдвиг промежуточной частоты
- **Система тестов**: Регрессионные тесты для всех стандартов в `rfgen/tests/`

### ⏳ В процессе:
- PSK-406 Message Builder (генерация HEX из beacon_id/lat/lon)
- Генерация битовых паттернов (FF00/F0F0/3333/5555)

### ❌ Не реализовано:
- PSK-406 FEC/интерлив (UI готов, кодирование TODO)
- Продвинутая телеметрия/метрики
- Pluto/USRP backends (скелет Pluto существует в `backends/pluto.py`)

## Недавние важные изменения

См. `rfgen/docs/CHANGELOG_2025-10-21.md` для полного списка. Основные обновления:

**✅ Реорганизация структуры проекта (2025-10-25):**
- Перенесена вся документация в `rfgen/docs/`
- Документация реализации стандартов в `rfgen/docs/implementation/`
- Все тесты в `rfgen/tests/`
- Чистый корень проекта с только ключевыми файлами

**✅ Полная реализация всех стандартов (2025-10-21 - 2025-10-25):**
- AIS с GMSK, guard sequences, crossfade
- DSC VHF/HF с phasing tones
- NAVTEX на трёх частотах (518/490/4209.5 кГц)
- 121.5 MHz с AM tone/sweep
- Default профили для всех 7 стандартов

**✅ Исправлена функциональность Save/Load профилей:**
- Расширена валидация для типов модуляций стандартов (BPSK, GMSK, FSK)
- Расширена валидация для паттернов стандартов (406, 121, AIS, DSC_VHF, DSC_HF, NAVTEX)
- Раздельные default.json файлы для каждого стандарта

**✅ Добавлена CF32 Naming Convention:**
- Стандартизованное именование: `iq_<FSk>_<name>.cf32`
- Автоматическое извлечение Fs из имени файла
- Fallback к 1024 кГц при отсутствии информации

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
2. Реализовать функцию генерации `build_xxx(profile) -> np.ndarray` (возвращает IQ-буфер)
3. Добавить новый тип стандарта в `utils/profile_io.py`:
   - В `defaults()`: добавить дефолтные параметры для нового стандарта
   - В `validate_profile()`: добавить модуляцию и паттерн в списки валидации
4. Создать новую страницу в `ui_qt/pages/page_new_standard.py`:
   - Наследовать от QWidget
   - Реализовать `_collect_profile()` - собирает данные из UI в профиль
   - Реализовать `_apply_profile_to_form()` - загружает профиль в UI
   - Реализовать `_load_default_profile()` - создаёт дефолты при первом запуске
   - Добавить автосохранение через `QTimer` с debounce 500ms
   - **ВАЖНО**: остановить автосохранение в начале `_apply_profile_to_form()` и запустить после
5. Добавить страницу в `main_window.py` (импорт, инициализация, добавление в sidebar и stack)
6. Если нужен CF32 вывод: использовать `utils/cf32_naming.py` для именования файлов

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
4. Добавить тип модуляции в `utils/profile_io.py` (валидация)
5. Обновить UI-элементы управления для отображения новых параметров

**Работа с CF32 файлами:**
```python
from rfgen.utils.cf32_naming import generate_cf32_name, parse_fs_from_filename

# При сохранении
filename = generate_cf32_name(fs_tx, "psk406")  # → iq_2000_psk406.cf32

# При загрузке
fs_hz, is_fallback = parse_fs_from_filename("iq_1024_ais.cf32")  # → (1024000, False)
```

**Работа с пересемплированием:**
```python
from rfgen.core.resample import resample_iq

# Генерация baseband на удобной частоте
iq_baseband = generate_signal(fs_baseband=500000)

# Пересемплирование к TX частоте
iq_tx = resample_iq(iq_baseband, fs_in=500000, fs_out=2000000)
```

**Важные технические детали для стандартов с непрерывной модуляцией (GMSK, FSK):**

При работе с AIS, DSC и другими стандартами с непрерывной фазовой модуляцией важно учитывать:

1. **Crossfade windows** - используйте окно `0.5 * (1 ± cos(π·n/(N-1)))` вместо `π·n/N` для идеального fade_out → 0 на последнем отсчёте (защита от off-by-one)

2. **Guard sequences** - для предотвращения скачков фазы к DC:
   - Pre-guard: 12-24 символа "единиц" перед преамбулой (warm-up фильтра)
   - Post-guard: 12-24 символа "единиц" после кадра (избегает transition → 0 Hz)

3. **Частоты дискретизации** - на Fs не кратных symbol rate (например, 2 МГц для 9600 бод):
   - `sps = int(fs/rs)` даёт небольшую ошибку Rs (9615.38 vs 9600)
   - Это нормально для большинства случаев
   - Для "идеала": увеличить `xfade_ms` до 1.0 мс или использовать resample к LCM

4. **Модуляционный индекс** - для GMSK: `h = 2·Δf/Rs`
   - AIS обычно: Δf=2400 Hz, Rs=9600 → h=0.5
   - Параметр задаётся через `standard_params['deviation_hz']`

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

## Тестирование

### Структура тестов
Все тесты находятся в `rfgen/tests/`:
- `test_ais_generation.py` - тесты генерации AIS
- `test_dsc_vhf_generation.py` - тесты DSC VHF
- `test_dsc_hf_generation.py` - тесты DSC HF
- `test_navtex_generation.py` - тесты NAVTEX
- `test_121p5_generation.py` - тесты 121.5 MHz
- `test_406_profile.py` - тесты профилей PSK-406
- `test_406_ui_methods.py` - тесты UI методов 406
- `test_default_profiles.py` - тесты default профилей
- `test_if_offset.py` - тесты IF offset

### Запуск тестов
```bash
# Запуск всех тестов
python -m pytest rfgen/tests/

# Запуск конкретного теста
python -m pytest rfgen/tests/test_ais_generation.py -v

# Запуск с выводом print-ов
python -m pytest rfgen/tests/ -v -s
```

### Ручное тестирование UI
После изменений в UI обязательно проверьте:
1. Открытие страницы без ошибок
2. Save Profile → Load Profile → проверка восстановления всех значений
3. Автосохранение (изменить значение → перезапустить UI → значение сохранилось)
4. Start/Stop функциональность

### Smoke-тесты для новых страниц
Минимальный набор тестов для новой страницы стандарта:
```python
# test_page_xxx.py
from rfgen.ui_qt.pages.page_xxx import PageXXX
from rfgen.utils.profile_io import validate_profile

page = PageXXX()
profile = page._collect_profile()
ok, msg = validate_profile(profile)
assert ok, f"Profile validation failed: {msg}"
print("[OK] Profile is valid")
```

### Регрессионное тестирование генерации
Проверка стабильности генерации сигнала:
```bash
# Генерация тестового файла
python -m rfgen.cli.rfgen_cli --mod FM --pattern Tone --outdir out --name regression_test

# Проверка наличия файла
ls out/regression_test.sc8

# Проверка в внешнем инструменте (inspectrum, URH, etc.)
```

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
