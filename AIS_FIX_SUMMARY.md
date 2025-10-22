# AIS Implementation - Complete Fix Summary

**Дата:** 2025-10-22
**Статус:** ✅ Полностью исправлено и протестировано

## Проблема

UI генерировал **неправильные** AIS сигналы:
- `best_eye=0.000` (закрытый eye diagram)
- `HDLC: found 0 frames` (демодулятор не находил фреймы)
- `CRC-X25: False` (CRC не проходил валидацию)

## Найденные причины

### 1. Неправильная частота дискретизации
- ❌ **Было:** Fs = 1024 кГц → SPS = 106.67 (не целое!)
- ✅ **Исправлено:** Fs = 960 кГц → SPS = 100 (целое)

**Проблема:** Дробное SPS приводит к накоплению ошибок выборки → ошибки CRC.

### 2. Неправильный импорт в UI
- ❌ **Было:** `from standards.ais import build_ais` (старая версия БЕЗ HDLC!)
- ✅ **Исправлено:** `from core.wave_engine import build_ais` (правильная версия)

**Старая версия (`standards/ais.py`) НЕ включала:**
- HDLC framing (преамбула, старт/стоп флаги, guard bits)
- Bit-stuffing (после 5 единиц вставить 0)
- CRC-16/X25 для FCS
- NRZI encoding
- Правильный upsampling (использовал zero insertion вместо repeat)

### 3. Неправильное чтение HEX из профиля
- ❌ **Было:** `build_ais()` читал только из `pattern.hex`
- ✅ **Исправлено:** читает из `standard_params.hex_message` (UI) + fallback на `pattern.hex` (тесты)

## Исправления

### Коммит 1: `590cfc4` - Реализация AIS согласно спецификации
**Файлы:** `core/wave_engine.py`

Добавлены функции:
- `_crc16_x25_ais()` - CRC-16/X25 (poly=0x8408)
- `_bytes_to_bits_lsb_first_ais()` - LSB-first bit conversion
- `_bit_stuff_ais()` - HDLC bit-stuffing
- `_nrzi_encode_ais()` - NRZI encoding
- `_gaussian_filter_ais()` - Gaussian filter (BT=0.4)
- `_gmsk_modulate_ais()` - GMSK modulation (h=0.5)
- `build_ais()` - главная функция генерации

### Коммит 2: `49f7e8d` - Исправление требований к Fs
**Файлы:** `docs/SPEC/AIS_msg_format.md`, `docs/task/2025-10-22_AIS_MSG.md`

**Обновлены требования:**
- ⚠️ **Fs ДОЛЖНА БЫТЬ КРАТНА 9600 Hz!**
- ✅ Рекомендовано: 960 кГц (SPS=100), 384 кГц (SPS=40), 192 кГц (SPS=20)
- ❌ НЕ использовать: 1024 кГц (SPS не целое)

### Коммит 3: `6a12e28` - Обновление default профиля
**Файлы:** `profiles/default_ais.json`

**Изменения:**
- `fs_tx: 2000000 → 960000` (правильная Fs!)
- `hex_message:` обновлен на эталонный тестовый HEX
- `target_hz: 162025000 → 161975000` (Channel A)
- `channel:` "A" → "Channel A (161.975 MHz)"

### Коммит 4: `166f0c8` - Исправление чтения HEX
**Файлы:** `core/wave_engine.py`

**Изменено:**
```python
# Было:
hex_payload = profile.get("pattern", {}).get("hex", "")

# Стало (поддержка UI + тестов):
hex_payload = (
    profile.get("standard_params", {}).get("hex_message", "") or
    profile.get("pattern", {}).get("hex", "")
)
```

### Коммит 5: `56083b6` - Исправление UI импортов
**Файлы:** `ui_qt/pages/page_ais.py`, `standards/ais.py`

**Изменения в `page_ais.py`:**
```python
# Было:
from ...standards.ais import build_ais  # ← СТАРАЯ версия!

# Стало:
from ...core.wave_engine import build_ais  # ← НОВАЯ правильная версия!
```

**Изменения в `standards/ais.py`:**
- Переименовано `build_ais()` → `build_ais_legacy()`
- Добавлены DEPRECATED warnings

## Результаты тестирования

### Round-trip тест (Fs=960 kHz)

**Входной HEX:**
```
481d6f345403ff33c8d603412140e10fff844e0006
```

**Результаты демодуляции:**
```
[DEMOD OK] Found 1 frame(s)
Bits:       184 (168 payload + 16 FCS)
CRC-X25:    True ✅
HEX (full): 481d6f345403ff33c8d603412140e10fff844e0006f3b6
Payload:    481d6f345403ff33c8d603412140e10fff844e0006
best_eye:   1.527 ✅ (открытый eye diagram!)
```

**Вывод:** ✅ **Полное совпадение с эталоном!**

### Проверка из UI

1. Запустить UI: `python -m rfgen.ui_qt.app`
2. Загрузить профиль: Profiles → Load → `default_ais.json`
3. Нажать Start
4. Результат: файл `iq_960_ais.cf32` с правильным CRC ✅

## Итоговая архитектура AIS

```
┌─────────────────────────────────────────────────────────────┐
│  HEX Payload (21 bytes)                                     │
│  481d6f345403ff33c8d603412140e10fff844e0006                 │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
         ┌─────────────────────┐
         │ CRC-16/X25 (FCS)    │ → f3b6 (little-endian)
         └──────────┬──────────┘
                    ↓
         ┌─────────────────────┐
         │ LSB-first conversion│ → 184 bits
         └──────────┬──────────┘
                    ↓
         ┌─────────────────────┐
         │ Bit-stuffing (HDLC) │ → +4 stuffed bits
         └──────────┬──────────┘
                    ↓
         ┌──────────────────────────────────────┐
         │ Frame assembly:                       │
         │  - Preamble (24 bits: 010101...)      │
         │  - Start flag (8 bits: 0x7E)          │
         │  - Stuffed payload+FCS (188 bits)     │
         │  - Stop flag (8 bits: 0x7E)           │
         │  - Guard (24 bits: 000...)            │
         └──────────┬───────────────────────────┘
                    ↓ Total: ~252 bits
         ┌─────────────────────┐
         │ NRZI encoding       │ → ±1 symbols
         └──────────┬──────────┘
                    ↓
         ┌─────────────────────┐
         │ GMSK modulation     │
         │  - Upsample (repeat)│ → SPS=100
         │  - Gaussian filter  │ → BT=0.4
         │  - Phase integration│ → h=0.5
         │  - exp(jφ)          │ → Complex IQ
         └──────────┬──────────┘
                    ↓
         ┌─────────────────────┐
         │ Add silence         │
         │  - pre: 20 ms       │
         │  - post: 20 ms      │
         └──────────┬──────────┘
                    ↓
         ┌─────────────────────┐
         │ Normalize to 0.8    │
         └──────────┬──────────┘
                    ↓
         ┌─────────────────────┐
         │ CF32 file (63600)   │
         │ Duration: 66.25 ms  │
         │ Fs: 960 kHz         │
         └─────────────────────┘
```

## Рекомендации для будущего

### Частота дискретизации
**ВСЕГДА используйте Fs кратную 9600 Hz:**
- ✅ **960 кГц** (SPS=100) — оптимально для точности
- ✅ **384 кГц** (SPS=40) — компактный размер файла
- ✅ **192 кГц** (SPS=20) — минимальная для демодуляции
- ❌ **1024 кГц** — НИКОГДА! (SPS не целое → ошибки CRC)

### Импорты
**ВСЕГДА импортируйте из правильного модуля:**
```python
from rfgen.core.wave_engine import build_ais  # ✅ ПРАВИЛЬНО
from rfgen.standards.ais import build_ais     # ❌ УСТАРЕЛО (legacy)
```

### Профили
**Структура профиля для AIS:**
```json
{
  "standard": "ais",
  "standard_params": {
    "hex_message": "481d6f345403ff33c8d603412140e10fff844e0006"
  },
  "device": {
    "fs_tx": 960000  // ← ВАЖНО: кратно 9600!
  }
}
```

## Файлы для тестирования

### Быстрый тест
```bash
python test_ais_quick.py
```

### Демодуляция
```bash
cd C:\work\TesterPi
python -m beacon406.AIS_cf32_to_HEX captures/iq_960_ais_spec_test.cf32
```

**Ожидаемый результат:**
- CRC-X25: True ✅
- best_eye: > 1.0 ✅
- Payload: полное совпадение ✅

## Коммиты

1. `590cfc4` - AIS: Реализация генерации согласно спецификации
2. `49f7e8d` - AIS: КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ - Fs должна быть кратна 9600 Hz
3. `6a12e28` - AIS: Обновлен default_ais.json профиль с правильной Fs
4. `166f0c8` - AIS: Исправлено чтение HEX из профиля (UI совместимость)
5. `56083b6` - AIS: UI КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ - использование правильной реализации

## Заключение

✅ **AIS модулятор полностью рабочий!**
- Round-trip тест пройден
- CRC валидация работает
- Eye diagram открытый
- UI генерирует правильные сигналы
- Совместимость с эталонным демодулятором TesterPi

**Готово к продакшену!** 🎉
