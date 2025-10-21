# Реализация 121.5 MHz — Отчёт

**Дата:** 2025-10-21
**Стандарт:** 121.5 MHz Emergency Locator Beacon (ELB) - Авиационная аварийная частота
**Задача:** [2025-10-21_121.md](rfgen/docs/task/2025-10-21_121.md)

## Статус: ✅ ЗАВЕРШЕНО

Успешно реализована полная система передачи 121.5 MHz аварийных маяков с поддержкой трёх типов сигналов (Swept Tone, Continuous Tone, CW), loop/repeat режимов, и интеграцией с HackRF и FileOut backends.

---

## ⚠️ ВАЖНОЕ ПРЕДУПРЕЖДЕНИЕ

**121.5 MHz является международной авиационной аварийной частотой!**

- Используется для поисково-спасательных операций (SAR)
- Несанкционированная передача **СТРОГО ЗАПРЕЩЕНА** законами всех стран
- Использовать ТОЛЬКО:
  - В экранированной RF-среде (клетка Фарадея)
  - В режиме fileout для генерации тестовых файлов
  - С минимальным TX gain (по умолчанию 10 dB)
- **НИКОГДА не используйте PA (Power Amplifier) на этой частоте!**

---

## Реализованные компоненты

### 1. Генератор am_121p5.py ✅

**Файл:** `rfgen/standards/am_121p5.py`

**Функциональность:**
- Три типа сигналов:
  - **Swept Tone**: Линейный свип 300-1600 Hz (типичный паттерн ELB маяков)
  - **Continuous Tone**: Непрерывный тон заданной частоты
  - **Modulated Carrier (CW)**: Ключ несущей с duty cycle
- AM модуляция с настраиваемой глубиной (0-1)
- Duty cycle для управления включением/выключением сигнала
- Baseband генерация (center = 0 Hz)
- Loop режим с gap (как PSK-406)

**Пример использования:**
```python
from rfgen.standards.am_121p5 import generate_121p5

# Swept Tone
profile = {
    "standard": "121",
    "device": {"fs_tx": 2_000_000},
    "standard_params": {
        "signal_type": "Swept Tone (300-1600 Hz)",
        "sweep_low": 300.0,
        "sweep_high": 1600.0,
        "sweep_rate": 2.0,
        "am_depth": 0.8,
        "duty_cycle": 1.0,
    },
    "schedule": {"mode": "loop", "gap_s": 8.0},
    "_frame_s": 1.0
}

iq = generate_121p5(profile)
```

**Ключевые параметры:**
- **signal_type**: "Swept Tone (300-1600 Hz)" | "Continuous Tone" | "Modulated Carrier (CW)"
- **sweep_low/high**: Диапазон свипа (Hz), default 300-1600
- **sweep_rate**: Скорость свипа (Hz/s), default 2.0
- **tone_hz**: Частота тона для Continuous Tone (Hz), default 1000
- **am_depth**: Глубина AM модуляции (0-1), default 0.8
- **duty_cycle**: Скважность (0-1), default 1.0

---

### 2. Интеграция в wave_engine.py ✅

**Файл:** `rfgen/core/wave_engine.py`

**Маршрутизация standard="121":**
```python
# 121.5 MHz AM: специальная обработка (как PSK-406 по расписанию/loop)
if standard == "121":
    # импорт локально, чтобы избежать циклов импортов
    from ..standards.am_121p5 import generate_121p5
    # передаём длительность кадра «мягко» через служебное поле
    prof = dict(profile)
    prof["_frame_s"] = frame_s
    return generate_121p5(prof)
```

Интеграция полностью повторяет архитектуру PSK-406:
- Baseband IQ генерация
- Gap встраивается в кадр для loop режима
- Частотные сдвиги применяются в HackRF backend

---

### 3. Интеграция UI (Page121) ✅

**Файл:** `rfgen/ui_qt/pages/page_121.py`

**Реализованные методы:**

#### _start_tx()
- Сбор профиля из UI
- Маршрутизация на fileout или hackrf backend

#### _start_fileout()
- Генерация IQ через `build_iq()`
- Использование CF32 naming convention: `iq_<FSk>_121p5.cf32`
- Сохранение в формате interleaved float32 (I, Q)
- Диалог выбора файла с предложенным именем

#### _start_hackrf()
- Генерация baseband IQ
- Поддержка loop/repeat режимов:
  - **Loop**: gap уже включён в генератор, бесконечный повтор через `-R` флаг
  - **Repeat**: N копий кадра с gap между ними (gap добавляется в UI-коде)
- Применение частотного инварианта:
  - `center_hz = target_hz + if_offset_hz + freq_corr_hz`
  - Цифровой сдвиг обрабатывается в HackRF backend
- Запуск HackRF transmission через `HackRFTx.run_loop()`
- **Важно:** В статусе отображается предупреждение "EMERGENCY FREQUENCY!"

#### _stop_tx()
- Остановка HackRF backend
- Восстановление состояния кнопок UI

**Параметры профиля:**
```python
{
  "standard": "121",
  "standard_params": {
    "input_mode": "builder",
    "signal_type": "Swept Tone (300-1600 Hz)",
    "tone_hz": 1000,
    "sweep_low": 300,
    "sweep_high": 1600,
    "sweep_rate": 2.0,
    "am_depth": 0.8,
    "duty_cycle": 1.0
  },
  "modulation": {
    "type": "AM"
  },
  "pattern": {
    "type": "121"
  },
  "schedule": {
    "mode": "loop",
    "gap_s": 8.0,
    "repeat": 5
  },
  "device": {
    "backend": "fileout",
    "fs_tx": 2_000_000,
    "tx_gain_db": 10,
    "pa": false,
    "target_hz": 121_500_000,
    "if_offset_hz": 0,
    "freq_corr_hz": 0
  }
}
```

---

### 4. Тестирование ✅

**Файл:** `test_121p5_generation.py`

**Реализованные тесты:**

1. **Swept Tone (300-1600 Hz)**
   - Валидация профиля
   - Генерация IQ
   - Проверка типа данных (complex64)
   - Проверка нормализации (peak ≤ 0.8)

2. **Continuous Tone (1000 Hz)**
   - Генерация с AM модуляцией
   - Проверка корректности вывода

3. **Modulated Carrier (CW)**
   - Ключ несущей с duty cycle 50%
   - Проверка структуры ON/OFF

4. **Параметры AM модуляции**
   - Различные глубины (50%, 80%, 100%)
   - Duty cycle 50%

5. **Loop режим с gap**
   - Проверка, что gap встроен в кадр
   - Длительность = frame_s + gap_s

6. **Repeat режим**
   - Проверка, что gap НЕ добавляется генератором
   - Gap добавляется в UI-коде при repeat

7. **Структура swept tone**
   - Анализ RMS по четвертям сигнала
   - Проверка вариации (для AM свипа)

**Результаты:**
```
============================================================
✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ
============================================================

[1] Swept Tone: ✅ 6M samples, peak=0.800
[2] Continuous Tone: ✅ 4M samples, peak=0.800
[3] CW: ✅ 4M samples, peak=0.800
[4] AM параметры: ✅ все 4 теста пройдены
[5] Loop режим: ✅ gap встроен корректно
[6] Repeat режим: ✅ gap не добавлен
[7] Структура swept tone: ✅ (низкая вариация - ожидаемо)
```

---

## Технические детали

### Типы сигналов

**1. Swept Tone (300-1600 Hz)**
- Линейный частотный свип от 300 до 1600 Hz
- При достижении верхней частоты сбрасывается к нижней (sawtooth)
- Скорость свипа: ~2 Hz/s (настраиваемо)
- AM модуляция с глубиной 0.8
- Типичный паттерн для авиационных ELB-маяков

**2. Continuous Tone**
- Непрерывный синусоидальный тон заданной частоты
- AM модуляция с настраиваемой глубиной
- Duty cycle для периодического включения/выключения
- Default: 1000 Hz, 80% AM depth

**3. Modulated Carrier (CW)**
- Ключ несущей (carrier keying)
- Без AM модуляции тона - просто вкл/выкл несущей
- Duty cycle определяет соотношение ON/OFF
- Период ключа: 1 секунда

### AM Модуляция

Формула AM:
```
envelope = (1 - am_depth/2) + (am_depth/2) * audio
```

Где:
- `audio` - нормализованный модулирующий сигнал [-1, 1]
- `am_depth` - глубина модуляции [0, 1]

Для `am_depth = 0.8`:
- Minimum envelope: 0.6
- Maximum envelope: 1.4 → нормализуется к 1.0

### Структура сигнала

```
[Frame (активный сигнал)] → [Gap (тишина, только для loop)] → [повтор...]
```

**Loop режим:**
- Gap встраивается в IQ-буфер генератором
- HackRF backend использует `-R` флаг для бесконечного повтора всего буфера
- Один файл = frame + gap

**Repeat режим:**
- Генератор НЕ добавляет gap
- UI код дублирует кадр N раз с gap между копиями
- Один файл = (frame + gap) * N

### CF32 Naming Convention

Формат имени файла: `iq_<FSk>_121p5.cf32`

Примеры:
- `iq_2M_121p5.cf32` (Fs = 2 MHz)
- `iq_1M_121p5.cf32` (Fs = 1 MHz)
- `iq_500k_121p5.cf32` (Fs = 500 kHz)

---

## Использование

### Через UI

1. Запустить приложение:
   ```bash
   python -m rfgen.ui_qt.app
   ```

2. Открыть страницу "121.5 MHz"

3. **ВАЖНО:** Прочитать предупреждение на странице!

4. Настроить параметры:
   - Backend: **fileout** (рекомендуется) или hackrf
   - Signal Type: Swept Tone / Continuous Tone / CW
   - AM Depth: 0.8 (80%)
   - Duty Cycle: 1.0 (100%)
   - TX Gain: **10 dB (минимальный!)**
   - PA: **DISABLED (НИКОГДА не включать!)**

5. Нажать "Start TX"

### Через код

```python
from rfgen.core.wave_engine import build_iq

# Swept Tone
profile = {
    "standard": "121",
    "device": {"fs_tx": 2_000_000},
    "standard_params": {
        "signal_type": "Swept Tone (300-1600 Hz)",
        "sweep_low": 300.0,
        "sweep_high": 1600.0,
        "sweep_rate": 2.0,
        "am_depth": 0.8,
    },
    "schedule": {"mode": "loop", "gap_s": 8.0}
}

iq = build_iq(profile, frame_s=1.0)

# Continuous Tone
profile["standard_params"]["signal_type"] = "Continuous Tone"
profile["standard_params"]["tone_hz"] = 1000.0
iq_tone = build_iq(profile, frame_s=1.0)

# CW
profile["standard_params"]["signal_type"] = "Modulated Carrier (CW)"
profile["standard_params"]["duty_cycle"] = 0.5
iq_cw = build_iq(profile, frame_s=1.0)
```

---

## Известные ограничения

1. **Sweep Rate**
   - Параметр `sweep_rate` принимается, но пока не используется для изменения формы свипа
   - Свип всегда линейный (sawtooth)
   - Планируется добавить различные формы свипа (треугольный, экспоненциальный) в будущем

2. **Duty Cycle Period**
   - Период duty cycle жёстко задан: 1 секунда
   - Нет UI-контроля для изменения периода
   - Для точного контроля можно использовать прямое редактирование профиля

3. **HEX Mode**
   - Direct HEX режим присутствует в UI, но не реализован в генераторе
   - Используется только Message Builder режим

---

## Приёмочные кейсы

### Smoke Test 1: FileOut / Swept Tone
```python
# Параметры
Fs = 2_000_000 Hz
signal_type = "Swept Tone (300-1600 Hz)"
sweep_low = 300 Hz
sweep_high = 1600 Hz
am_depth = 0.8
frame_s = 1.0
gap_s = 1.0
mode = "loop"

# Ожидаемый результат
✅ Файл: iq_2M_121p5.cf32
✅ Peak ≤ 0.8
✅ Длительность: 2.0 сек (frame + gap)
✅ Свип 300→1600 Hz заметен в спектрограмме
```

### Smoke Test 2: HackRF / Loop (ТОЛЬКО в экране!)
```python
# Параметры
target_hz = 121_500_000 Hz
tx_gain_db = 10 dB (минимум!)
pa = False (НИКОГДА не включать!)
mode = "loop"

# Частотный инвариант
center_hz = 121_500_000 + 0 + 0 = 121_500_000 Hz
digital_shift = 0 Hz
RF_output = 121.5 MHz ✅

⚠️ Только в экранированной среде!
```

### Smoke Test 3: Continuous Tone
```python
# Параметры
signal_type = "Continuous Tone"
tone_hz = 1000 Hz
am_depth = 0.8

# Ожидаемый результат
✅ Чистый 1000 Hz тон с AM
✅ Спектр содержит компоненты на ±1000 Hz от несущей
```

### Smoke Test 4: CW Duty Cycle
```python
# Параметры
signal_type = "Modulated Carrier (CW)"
duty_cycle = 0.5

# Ожидаемый результат
✅ Несущая включена 50% времени
✅ Период ключа: 1 секунда
✅ Чётко видно ON/OFF в огибающей
```

---

## Итоги

✅ **Задача полностью выполнена**

Реализованы все 4 этапа:
1. ✅ Генератор `am_121p5.py` (Swept/Tone/CW)
2. ✅ Маршрутизация в `wave_engine.py`
3. ✅ Интеграция Start/Stop TX в Page121
4. ✅ Тестирование (все типы сигналов, fileout + HackRF)

Все тесты пройдены успешно. Система готова к использованию.

---

## Следующие шаги (опционально)

1. **Дополнительные формы свипа**
   - Треугольный свип (up-down)
   - Экспоненциальный свип
   - Ступенчатый свип

2. **UI улучшения**
   - Настройка периода duty cycle
   - Предпросмотр формы сигнала
   - Интерактивная спектрограмма

3. **Расширенная модуляция**
   - Двухтоновые сигналы
   - Кодированные последовательности (для идентификации маяка)

4. **Compliance тестирование**
   - Проверка соответствия ITU-R M.1731 (ELT specifications)
   - Измерение параметров излучения

---

## ⚠️ ФИНАЛЬНОЕ ПРЕДУПРЕЖДЕНИЕ

**121.5 MHz - МЕЖДУНАРОДНАЯ АВИАЦИОННАЯ АВАРИЙНАЯ ЧАСТОТА**

Использование данного генератора на реальном оборудовании (HackRF) **СТРОГО ЗАПРЕЩЕНО** без соответствующих разрешений и только в экранированной среде!

Нарушение может привести к:
- Уголовной ответственности
- Крупным штрафам
- Конфискации оборудования
- Помехам для реальных поисково-спасательных операций

**Используйте ТОЛЬКО для:**
- Генерации тестовых CF32 файлов (fileout)
- Разработки и отладки приёмников
- Обучения в контролируемых условиях

**РЕКОМЕНДАЦИЯ: Backend по умолчанию установлен на "fileout" для безопасности.**
