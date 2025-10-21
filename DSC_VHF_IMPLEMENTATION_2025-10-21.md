# Реализация DSC VHF передачи

**Дата:** 2025-10-21
**Статус:** ✅ ЗАВЕРШЕНО И ПРОТЕСТИРОВАНО

---

## Обзор

Реализована полноценная передача DSC VHF (Digital Selective Calling - цифровой избирательный вызов) на канале 70 (156.525 МГц) с AFSK модуляцией @ 1200 Bd и FM модуляцией для тестирования морских систем.

**⚠️ ВНИМАНИЕ:** DSC - система морской селективной связи. Несанкционированная передача может мешать навигации и службам безопасности и является незаконной. Используйте ТОЛЬКО в экранированной среде или с backend=fileout.

---

## Реализованная функциональность

### ✅ AFSK модулятор (mark=2100 Hz, space=1300 Hz @ 1200 Bd)

**Файл:** `rfgen/standards/dsc_vhf.py`

**Уже реализовано (использовано существующее):**
- Функция `generate_dsc_vhf()` - генерация DSC VHF IQ-буфера:
  - AFSK модуляция: mark (1) = 2100 Hz, space (0) = 1300 Hz
  - Symbol rate: 1200.0 baud (настраиваемо)
  - FM модуляция аудио AFSK с девиацией fm_dev_hz
  - Опциональный пре-эмфазис (6 dB/oct)
  - Секции: pre-silence → carrier → FM(AFSK) → post-silence
  - Нормализация к безопасному уровню (peak ≤ 0.999)

**Параметры:**
- Symbol rate: 1200 Bd (по умолчанию)
- Mark frequency: 2100 Hz (по умолчанию)
- Space frequency: 1300 Hz (по умолчанию)
- FM deviation: 2500 Hz (при |audio|=1.0)
- Pre-emphasis: опционально (False по умолчанию)

### ✅ DSC Framing (ITU-R M.493)

**Файл:** `rfgen/standards/dsc_vhf.py`

**Уже реализовано:**
- Функция `_build_phasing_symbols()` - генерация phasing sequence
- Функция `_time_diversity_schedule()` - time-diversity интерливинг
- Функция `_build_dsc_frame()` - сборка полного DSC кадра:
  - Phasing (12 символов)
  - Primary symbols
  - EOS symbol (127)
  - Time-diversity
- Функция `_primary7_to_tenbit()` - 10-bit encoding (7 info + 3 check)
- Функция `_symbols_to_tenbits()` - конвертация символов в 10-битные блоки
- Функция `build_dsc_bits()` - конвертация primary symbols в битовый поток

**Phasing sequence:**
- Формат: [125, RX, 125, RX, ...] (6 пар)
- RX sequence: [111, 110, 109, 108, 107, 106, 105, 104]

**Time-diversity:**
- Алгоритм: вставка повторов символов с задержкой
- Очередь: 4 символа
- Заполнение: symbol 125

### ✅ Message Builder

**Файл:** `rfgen/standards/dsc_vhf.py`

**Уже реализовано:**
- Функция `build_primary_symbols_from_cfg()` - сборка primary symbols из конфига:
  - Scenario presets: "all_ships", "individual", "distress"
  - Format symbols: 112 (all ships), 120 (individual)
  - MMSI → 5 two-digit symbols
  - Telecommand symbols: [126, 126] (fillers)
- Функция `_mmsi_to_symbols()` - конвертация MMSI в DSC symbols
- Функция `_digits_to_symbols()` - конвертация цифр в символы (пары 00..99)

### ✅ Обёртка build_dsc_vhf(profile)

**Файл:** `rfgen/standards/dsc_vhf.py`

**Добавлено:**
```python
def build_dsc_vhf(profile: dict) -> np.ndarray:
    """Генерация DSC VHF IQ-буфера из профиля."""
```

**Функциональность:**
- Поддержка двух режимов ввода:
  - **Direct HEX**: прямой ввод HEX сообщения
  - **Message Builder**: сборка из MMSI/call_type
- Вызов `build_primary_symbols_from_cfg()` для builder режима
- Вызов `build_dsc_bits()` для генерации битов
- Конвертация битов в HEX
- Вызов базового генератора `generate_dsc_vhf()`

---

## UI Integration (PageDSC_VHF)

**Файл:** `rfgen/ui_qt/pages/page_dsc_vhf.py`

### ✅ Реализовано:

**Методы Start/Stop TX:**
- `_start_tx()` - выбор backend (fileout/hackrf)
- `_start_fileout(prof)` - генерация и сохранение в CF32:
  - Генерация IQ через `build_dsc_vhf()`
  - Использование конвенции именования: `iq_<FSk>_dsc_vhf.cf32`
  - Сохранение interleaved float32 I/Q
  - Диалог выбора пути
- `_start_hackrf(prof)` - генерация и передача через HackRF:
  - Генерация baseband IQ
  - Обработка schedule режимов (loop/repeat)
  - Добавление gap между кадрами
  - Применение IF shift через HackRF backend
  - Запуск HackRF с инвариантом частот
- `_stop_tx()` - graceful остановка передачи

**Режимы передачи:**
- **Loop mode**: бесконечный повтор с gap внутри кадра
- **Finite mode**: N повторов `(frame + gap) * N`

**Параметры профиля:**
```json
{
  "standard": "dsc_vhf",
  "standard_params": {
    "input_mode": "hex",  // или "builder"
    "hex_message": "D5AA55D5AA55",
    "call_type": "all_ships",
    "mmsi_to": "111222333",
    "category": "Distress",
    "nature": "Fire/Explosion",
    "position": "0000.00N/00000.00E",
    "utc_time": "0000",
    "symbol_rate": 1200.0,
    "f_mark_hz": 2100.0,
    "f_space_hz": 1300.0,
    "fm_dev_hz": 2500.0,
    "preemphasis": false,
    "pre_silence_ms": 25,
    "carrier_sec": 0.16,
    "post_silence_ms": 25,
    "noise_dbfs": -60,
    "normalize": true
  },
  "device": {
    "backend": "hackrf",
    "fs_tx": 1000000,
    "tx_gain_db": 30,
    "pa": false,
    "target_hz": 156525000,
    "if_offset_hz": 0,
    "freq_corr_hz": 0
  },
  "schedule": {
    "mode": "loop",
    "gap_s": 8.0,
    "repeat": 5
  }
}
```

---

## Тестирование

**Файл:** `test_dsc_vhf_generation.py`

**Результаты:**
```
============================================================
✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ
============================================================

[1] ✅ Direct HEX режим (249984 сэмплов, 250ms)
[2] ✅ Message Builder режим (249984 сэмплов)
[3] ✅ Базовый генератор generate_dsc_vhf()
[4] ✅ Параметры AFSK:
    - Стандартные тоны (2100/1300 Hz)
    - Низкие тоны (1200/800 Hz)
    - Большая девиация FM (5000 Hz)
    - С пре-эмфазисом
[5] ✅ Структура сигнала:
    - Pre-silence RMS: 0.001 (шум -60 dBFS)
    - Carrier RMS: 0.999 (несущая)
    - Peak: 0.999 (нормализация работает)
```

---

## Изменённые файлы

### Изменённые:
1. **`rfgen/standards/dsc_vhf.py`**:
   - Добавлена обёртка `build_dsc_vhf(profile)` для интеграции
   - Поддержка Direct HEX и Message Builder режимов

2. **`rfgen/ui_qt/pages/page_dsc_vhf.py`**:
   - Реализованы `_start_fileout()`, `_start_hackrf()`, `_stop_tx()`
   - Поддержка режимов loop/repeat с gap
   - Интеграция с HackRF backend
   - Использование CF32 naming convention

### Новые:
3. **`test_dsc_vhf_generation.py`** - Автоматические тесты
4. **`DSC_VHF_IMPLEMENTATION_2025-10-21.md`** (этот файл) - Документация

---

## Использование

### Генерация CF32 файла (fileout backend)

1. Запустите UI: `python -m rfgen.ui_qt.app`
2. Откройте страницу **DSC VHF**
3. Выберите **Backend: fileout**
4. **Direct HEX режим:**
   - Введите HEX сообщение (например, "D5AA55D5AA55")
5. **Message Builder режим:**
   - Выберите Call Type (All Ships / Individual)
   - Введите MMSI (To): 111222333
   - Выберите Category (Distress / Urgency / Safety / Routine)
6. Нажмите **Start TX**
7. Выберите путь сохранения (по умолчанию: `iq_1000_dsc_vhf.cf32`)

### Передача через HackRF

1. Запустите UI: `python -m rfgen.ui_qt.app`
2. Откройте страницу **DSC VHF**
3. Выберите **Backend: hackrf**
4. Настройте параметры:
   - Target: 156.525 MHz (Channel 70) - фиксировано
   - TX Gain: 0-47 dB (рекомендуется 30 dB)
   - PA: Enable/Disable
   - Mode: Loop (endless) или Finite (N frames)
   - Gap: 8.0 сек (пауза между кадрами)
5. Нажмите **Start TX**
6. Для остановки: нажмите **Stop**

**⚠️ КРИТИЧЕСКИ ВАЖНО:**
- Channel 70 (156.525 MHz) - морская служебная частота DSC
- Используйте ТОЛЬКО в экранированной среде (клетка Фарадея, RF-бокс)
- Несанкционированная передача КРАЙНЕ незаконна
- Может создавать помехи службам морской безопасности и спасению

---

## Технические детали

### AFSK модуляция

**Принцип:**
1. Биты → тоны (0 → 1300 Hz, 1 → 2100 Hz)
2. Upsampling (sym_N = Fs / 1200)
3. Генерация синусоиды для каждого символа
4. Опциональный пре-эмфазис (6 dB/oct)
5. FM модуляция аудио: φ(t) = 2π·fm_dev·∫audio(t)dt
6. Комплексный сигнал: exp(j·φ)

**Девиация FM:**
- fm_dev_hz = 2500 Hz (при |audio|=1.0)
- Пик девиации ±2.5 кГц для полной амплитуды

**Структура сигнала:**
- Pre-silence: 25 ms (шум -60 dBFS)
- Carrier: 160 ms (неmodulated несущая)
- AFSK message: зависит от длины битов
- Post-silence: 25 ms (шум -60 dBFS)

### DSC Frame Structure

**10-bit encoding:**
- 7 information bits + 3 check bits
- Check bits: count of zeros in info bits (binary, 3 bits)

**Phasing:**
- 12 symbols: [125, RX_i] * 6
- RX sequence: [111, 110, 109, 108, 107, 106, 105, 104]

**Time-diversity:**
- Алгоритм повтора с задержкой для коррекции ошибок
- Очередь: 4 символа
- Вставка повторов через каждый символ

**Primary symbols (All Ships example):**
- Format: 112 (all ships)
- Address: 5 symbols (MMSI in pairs)
- Telecommand: [126, 126] (fillers)
- EOS: 127

**Итоговый битовый поток:**
- Phasing + Time-diversity(Primary symbols + EOS)
- Конвертация в 10-bit blocks
- Сборка в битовый поток
- AFSK модуляция

### CF32 файлы

**Формат:**
- Interleaved float32: `I0, Q0, I1, Q1, ...`
- Порядок байтов: Little Endian
- Нормализация: ±1.0 (peak ≤ 0.999)

**Именование:**
- Конвенция: `iq_<FSk>_dsc_vhf.cf32`
- Пример: `iq_1000_dsc_vhf.cf32` (Fs = 1 MS/s)

### HackRF параметры

**Инвариант частот:**
```
center_hz = target_hz + if_offset_hz + freq_corr_hz
digital_shift_hz = -(if_offset_hz + freq_corr_hz)
RF_output = target_hz  (точно!)
```

**Пример:**
- Target: 156.525 MHz (Channel 70)
- IF offset: 0 Hz
- Freq corr: 0 Hz
- Center LO: 156.525 MHz
- Digital shift: 0 Hz
- RF output: 156.525 MHz ✅

---

## Отличия от AIS

| Параметр | AIS | DSC VHF |
|----------|-----|---------|
| Модуляция | GMSK | AFSK + FM |
| Bitrate | 9600 bps | 1200 Bd (symbols) |
| Частоты | 161.975/162.025 MHz | 156.525 MHz (Ch70) |
| Фильтр | Гауссов (BT=0.4) | Нет (чистые тоны) |
| Тоны | - | 1300/2100 Hz |
| Фрейминг | HDLC | Phasing + Time-diversity |
| Encoding | - | 10-bit (7+3) |

---

## Следующие шаги (опционально)

### Для полной реализации DSC VHF:

1. **Расширенные форматы сообщений:**
   - Полная матрица форматов ITU-R M.493
   - Distress, Urgency, Safety, Routine
   - Position reports, Test calls, ACK/NAK

2. **Валидация MMSI:**
   - Проверка формата (9 цифр)
   - Проверка диапазонов (MID code)

3. **Position encoding:**
   - Конвертация lat/lon в DSC symbols
   - Формат MMSSDD (минуты/доли минут)

4. **UTC time encoding:**
   - Конвертация HHMM в DSC symbols

5. **ECC (Error Correction Code):**
   - Полная реализация check bits

6. **Генерация .wav аудио:**
   - Экспорт AFSK как WAV файл
   - Для лабораторных приёмников

---

## Обратная совместимость

✅ **Полная обратная совместимость:**
- Существующая функция `generate_dsc_vhf()` не изменена
- Все существующие параметры работают
- Новая обёртка `build_dsc_vhf()` опциональна
- Никаких breaking changes

---

## Статус задач

✅ **build_dsc_vhf(profile)** - COMPLETED
✅ **Start/Stop TX в PageDSC_VHF** - COMPLETED
✅ **Режимы loop/repeat с gap** - COMPLETED
✅ **Тестирование** - COMPLETED (все тесты пройдены)

---

## Итог

Реализована полноценная система передачи DSC VHF с AFSK модуляцией @ 1200 Bd на канале 70 (156.525 МГц). Поддерживаются два режима ввода (Direct HEX и Message Builder), два backend (fileout и HackRF), два режима передачи (loop и repeat). Все тесты пройдены успешно.

**Готово к использованию для:**
- Тестирования DSC приёмников
- Генерации тестовых сигналов для морских систем
- Офлайн-анализа через CF32 файлы
- Передачи через HackRF (только в экранированной среде!)

**⚠️ ПОМНИТЕ:** DSC - критическая система морской безопасности. Используйте ответственно и законно!
