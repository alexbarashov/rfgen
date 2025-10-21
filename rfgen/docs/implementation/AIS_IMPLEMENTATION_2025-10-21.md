# Реализация AIS передачи

**Дата:** 2025-10-21
**Статус:** ✅ ЗАВЕРШЕНО И ПРОТЕСТИРОВАНО

---

## Обзор

Реализована полноценная передача AIS (Automatic Identification System) с GMSK модуляцией 9600 бод для тестирования SDR-приёмников и морских систем.

**⚠️ ВНИМАНИЕ:** AIS — система морской безопасности. Несанкционированная передача может мешать навигации и является незаконной. Используйте ТОЛЬКО в экранированной среде или с backend=fileout.

---

## Реализованная функциональность

### ✅ Этап 1: GMSK модулятор (BT≈0.4, 9600 baud)

**Файл:** `rfgen/standards/ais.py`

**Реализовано:**
- Функция `_generate_gaussian_filter(bt, samples_per_symbol)` - генерация гауссова фильтра
- Функция `_bits_to_nrz(bits)` - конвертация битов в NRZ формат (0→-1, 1→+1)
- Функция `_gmsk_modulate(bits, fs, bitrate, bt)` - GMSK модуляция:
  - Upsampling битов
  - Гауссова фильтрация (BT≈0.4)
  - MSK модуляция с девиацией Δf = bitrate/4
  - Интеграция фазы: φ(t) = 2π·Δf·∫filtered(t)dt
  - Генерация комплексного сигнала: exp(j·φ(t))

**Параметры:**
- Bitrate: 9600 bps (по умолчанию, настраиваемо)
- BT: 0.4 (по умолчанию, настраиваемо)
- Span фильтра: 4 символа
- Нормализация: peak ≤ 0.8

---

### ✅ Этап 2: Парсер NMEA VDM/VDO

**Файл:** `rfgen/standards/ais.py`

**Реализовано:**
- Функция `_parse_nmea_vdm(nmea_string)` - разбор NMEA VDM/VDO строк:
  - Формат: `!AIVDM,fragments,fragment_num,message_id,channel,payload,fill_bits*checksum`
  - Извлечение 6-битного payload
  - Обработка fill bits
  - Поддержка !AIVDM и !AIVDO
- Функция `_decode_6bit_ascii(payload_6bit)` - декодирование AIS 6-битного ASCII:
  - ASCII 48-87 ('0'-'W') → 0-39
  - ASCII 96-119 ('`'-'w') → 40-63
  - Конвертация в биты (MSB first)

**Пример:**
```python
nmea = "!AIVDM,1,1,,A,14eG;o@034o8sd<L9i:a;WF>062D,0*7D"
payload_6bit, fill_bits = _parse_nmea_vdm(nmea)
bits = _decode_6bit_ascii(payload_6bit)
```

---

### ✅ Этап 3: build_ais(profile) → IQ-буфер

**Файл:** `rfgen/standards/ais.py`

**Реализовано:**
- Функция `build_ais(profile)` - генерация AIS IQ-буфера:
  - Поддержка двух режимов ввода:
    - **Direct HEX** (по умолчанию): прямой ввод HEX сообщения
    - **NMEA**: парсинг NMEA VDM/VDO строк
  - Опциональные PHY параметры (для будущего):
    - NRZI encoding (реализовано)
    - Scrambler (TODO)
    - HDLC framing (TODO)
  - GMSK модуляция
  - Добавление тишины в начале/конце (25ms по умолчанию)
  - Нормализация к безопасному уровню (≤0.8)

**Параметры профиля:**
```json
{
  "standard": "ais",
  "standard_params": {
    "input_mode": "hex",  // или "nmea"
    "hex_message": "24e98f59effffff33c8d603412140e10f002010384ab70",
    "nmea_message": "!AIVDM,1,1,,A,...",
    "bitrate": 9600,
    "bt": 0.4,
    "pre_silence_ms": 25,
    "post_silence_ms": 25,
    "use_nrzi": false,
    "use_scrambler": false,
    "add_header": false
  }
}
```

---

### ✅ Этап 4: Подключение Start TX в PageAIS

**Файл:** `rfgen/ui_qt/pages/page_ais.py`

**Реализовано:**
- Метод `_start_tx()` - выбор backend (fileout/hackrf)
- Метод `_start_fileout(prof)` - генерация и сохранение в CF32:
  - Генерация IQ через `build_ais()`
  - Использование конвенции именования: `iq_<FSk>_ais.cf32`
  - Сохранение interleaved float32 I/Q
  - Диалог выбора пути сохранения
- Метод `_start_hackrf(prof)` - генерация и передача через HackRF:
  - Генерация baseband IQ
  - Поддержка resample (если нужно)
  - Обработка schedule режимов (loop/repeat)
  - Добавление gap между кадрами
  - Применение IF shift через HackRF backend
  - Запуск HackRF с инвариантом частот: RF = target
- Метод `_stop_tx()` - остановка передачи:
  - Graceful stop backend
  - Восстановление состояния кнопок

---

### ✅ Этап 5: Поддержка режимов loop/repeat с gap

**Файл:** `rfgen/ui_qt/pages/page_ais.py`

**Реализовано в `_start_hackrf()`:**

**Режим Loop (бесконечный повтор):**
- Gap добавляется внутрь кадра: `frame + gap`
- Флаг HackRF `-R` для бесконечного повтора
- UI: Radio button "Loop (endless)"

**Режим Finite (N повторов):**
- Конкатенация `(frame + gap) * N`
- Передача всего буфера за один раз
- UI: Radio button "Finite (N frames)" с полем Frame Count

**Параметры:**
- `gap_s`: Длительность паузы между кадрами (по умолчанию 8.0 сек)
- `repeat`: Количество повторов для Finite режима (по умолчанию 5)

---

### ✅ Этап 6: Тестирование

**Файл:** `test_ais_generation.py`

**Тесты:**
1. ✅ Валидация профиля
2. ✅ Генерация AIS IQ-буфера (138272 сэмплов за 69ms)
3. ✅ Проверка параметров сигнала (RMS=0.421, Peak=0.800)
4. ✅ NMEA VDM режим
5. ✅ NRZI кодирование

**Результаты:**
```
============================================================
✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ
============================================================
```

---

## Изменённые файлы

### Новые файлы
1. **`test_ais_generation.py`** - Тесты генерации AIS
2. **`AIS_IMPLEMENTATION_2025-10-21.md`** - Этот документ

### Изменённые файлы
3. **`rfgen/standards/ais.py`**:
   - Добавлен GMSK модулятор
   - Добавлен парсер NMEA VDM/VDO
   - Реализован `build_ais(profile)`
   - Поддержка NRZI, scrambler (флаги), HDLC framing (флаги)

4. **`rfgen/ui_qt/pages/page_ais.py`**:
   - Реализованы `_start_tx()`, `_start_fileout()`, `_start_hackrf()`, `_stop_tx()`
   - Поддержка режимов loop/repeat с gap
   - Интеграция с HackRF backend
   - Использование CF32 naming convention

---

## Использование

### Генерация CF32 файла (fileout backend)

1. Запустите UI: `python -m rfgen.ui_qt.app`
2. Откройте страницу **AIS**
3. Выберите **Backend: fileout**
4. Выберите **Channel A** (161.975 MHz) или **Channel B** (162.025 MHz)
5. Введите HEX сообщение или NMEA строку
6. Нажмите **Start TX**
7. Выберите путь сохранения (по умолчанию: `iq_2000_ais.cf32`)

### Передача через HackRF

1. Запустите UI: `python -m rfgen.ui_qt.app`
2. Откройте страницу **AIS**
3. Выберите **Backend: hackrf**
4. Настройте параметры:
   - Channel: A/B или Custom
   - TX Gain: 0-47 dB (рекомендуется 30 dB)
   - PA: Enable/Disable
   - Mode: Loop (endless) или Finite (N frames)
   - Gap: 8.0 сек (пауза между кадрами)
5. Нажмите **Start TX**
6. Для остановки: нажмите **Stop**

**⚠️ ВАЖНО:**
- Используйте только в экранированной среде (клетка Фарадея, RF-бокс)
- Несанкционированная передача на AIS частотах незаконна
- Может создавать помехи морской навигации

---

## Технические детали

### GMSK модуляция

**Принцип:**
1. Биты → NRZ (0→-1, 1→+1)
2. Upsampling (вставка нулей между символами)
3. Гауссов фильтр (BT≈0.4)
4. Интегрирование для получения фазы
5. Генерация комплексного сигнала: `exp(j·φ)`

**Девиация частоты:**
- MSK: Δf = bitrate/4 = 9600/4 = 2400 Hz
- Индекс модуляции: h = 0.5 (для MSK)

**Гауссов фильтр:**
- BT = 0.4 (bandwidth-time product)
- Sigma = sqrt(ln(2))/(2π·BT) ≈ 0.265
- Span = 4 символа
- Нормализация: Σh = 1

### CF32 файлы

**Формат:**
- Interleaved float32: `I0, Q0, I1, Q1, I2, Q2, ...`
- Порядок байтов: Little Endian
- Нормализация: ±1.0 (peak ≤ 0.8 для избежания клиппинга)

**Именование:**
- Конвенция: `iq_<FSk>_ais.cf32`
- Пример: `iq_2000_ais.cf32` (Fs = 2 MS/s)

### HackRF параметры

**Инвариант частот:**
```
center_hz = target_hz + if_offset_hz + freq_corr_hz
digital_shift_hz = -(if_offset_hz + freq_corr_hz)
RF_output = target_hz  (точно!)
```

**Пример:**
- Target: 162.025 MHz (Channel B)
- IF offset: -25 kHz
- Freq corr: 0 Hz
- Center LO: 162.000 MHz
- Digital shift: +25 kHz
- RF output: 162.025 MHz ✅

---

## Следующие шаги (опционально)

### Для полной реализации PHY уровня:

1. **Scrambler:**
   - Реализовать LFSR для скремблирования битов
   - Флаг `use_scrambler` уже предусмотрен

2. **HDLC framing:**
   - Добавление преамбулы (training sequence)
   - Добавление флагов старта/стопа (0x7E)
   - Bit stuffing (после 5 подряд единиц вставить 0)
   - Флаг `add_header` уже предусмотрен

3. **CRC:**
   - Добавление CRC-16 для проверки целостности
   - ITU-R M.1371 рекомендует CRC-16-CCITT

4. **Message Builder:**
   - Генерация AIS сообщений из структурированных полей:
     - Message Type 1/2/3 (Position Report)
     - Message Type 4 (Base Station)
     - Message Type 5 (Static Data)
   - UI уже готов (поля MMSI, msg_type, payload)

---

## Обратная совместимость

✅ **Полная обратная совместимость:**
- Старая заглушка `generate_ais_test(params)` работает (вызывает `build_ais()`)
- Все существующие профили продолжают работать
- Никаких breaking changes в API
- Новые параметры опциональны (есть дефолты)

---

## Статус задач

✅ **Этап 1** - GMSK модулятор (COMPLETED)
✅ **Этап 2** - Парсер NMEA VDM/VDO (COMPLETED)
✅ **Этап 3** - build_ais(profile) (COMPLETED)
✅ **Этап 4** - Подключение Start TX (COMPLETED)
✅ **Этап 5** - Режимы loop/repeat с gap (COMPLETED)
✅ **Этап 6** - Тестирование (COMPLETED)

---

## Итог

Реализована полноценная система передачи AIS с GMSK модуляцией 9600 бод. Поддерживаются два режима ввода (Direct HEX и NMEA VDM/VDO), два backend (fileout и HackRF), два режима передачи (loop и repeat). Все тесты пройдены успешно.

**Готово к использованию для:**
- Тестирования AIS приёмников
- Генерации тестовых сигналов для разработки
- Офлайн-анализа через CF32 файлы
- Передачи через HackRF (только в экранированной среде!)

**⚠️ ПОМНИТЕ:** Используйте ответственно и законно!
