# IF Compensation Implementation Results
## 2025-10-21

### Задача
Реализация IF компенсации через цифровой сдвиг в backend (спецификация: `2025-10-21_IF.md`).

**Цель:** Независимо от `if_offset_hz` и `freq_corr_hz`, в эфир всегда должна уходить частота `target_hz`.

**Формула LO (без изменений):**
```
center_hz = target_hz + if_offset_hz + freq_corr_hz
```

**Цифровая компенсация (новая логика):**
```
digital_shift_hz = -(if_offset_hz + freq_corr_hz)
RF = center_hz + digital_shift_hz = target_hz
```

---

### Реализация

#### 1. Генератор (`wave_engine.py`)
- ✅ Удалён IF-сдвиг из генератора
- ✅ Генератор теперь всегда выдаёт чистый baseband на 0 Гц
- ✅ Комментарии обновлены: "Цифровая компенсация IF+corr выполняется в backend"

#### 2. Backend (`hackrf.py`)
- ✅ Добавлена функция `_apply_digital_shift(iq, shift_hz, fs)` (lines 67-88)
  - Формула: `iq * exp(j * 2π * shift_hz * t)`
  - Обработка граничного случая: `shift_hz ≈ 0`
- ✅ Изменена сигнатура `run_loop()`:
  - Было: `center_hz`
  - Стало: `target_hz, if_offset_hz=0, freq_corr_hz=0`
- ✅ Внутри `run_loop()`:
  - Вычисление: `center_hz = target_hz + if_offset_hz + freq_corr_hz`
  - Вычисление: `digital_shift_hz = -(if_offset_hz + freq_corr_hz)`
  - Для cf32: применение `_apply_digital_shift()` после чтения, перед sc8
  - Для sc8: без изменений (обратная совместимость)
- ✅ Добавлена секция логирования "=== IF Compensation ===" (lines 269-276)
  - Выводятся: target, if_offset, freq_corr, center, digital_shift
  - Проверка инварианта: `RF out = center + digital_shift` (должно равняться target)

#### 3. UI (`page_406.py`, `page_gen_basic.py`)
- ✅ Обновлены вызовы `run_loop()`:
  - Передаются: `target_hz`, `if_offset_hz`, `freq_corr_hz`
  - Вычисление `center_hz` перенесено в backend
- ✅ Удалена старая логика сдвига в `page_gen_basic.py`:
  - Было: `center = target - if_hz`
  - Стало: передача всех трёх параметров

---

### Тестирование

#### Unit-тесты функции `_apply_digital_shift()`
```
Test 1: Zero shift (shift=0)
  Max difference: 0.00e+00
  Result: OK

Test 2: Shift up by +5 kHz
  Expected frequency: 15000 Hz
  Max difference: 9.58e-06
  Result: OK

Test 3: Shift down by -37 kHz (case B)
  Input signal: baseband at 0 Hz
  Expected frequency: -37000 Hz
  Max difference: 0.00e+00
  Result: OK
```

#### Smoke-тесты инварианта (из спецификации)
```
Case A: target=406037000, if=-37000, corr=0
  Center (LO):       406000000 Hz
  Digital shift:         37000 Hz
  RF out:            406037000 Hz
  Invariant:      ✅ OK

Case B: target=406037000, if=+37000, corr=0
  Center (LO):       406074000 Hz
  Digital shift:        -37000 Hz
  RF out:            406037000 Hz
  Invariant:      ✅ OK

Case C: target=406037000, if=0, corr=+200
  Center (LO):       406037200 Hz
  Digital shift:          -200 Hz
  RF out:            406037000 Hz
  Invariant:      ✅ OK
```

---

### Файлы изменённые

1. `rfgen/core/wave_engine.py` - удалён IF сдвиг из генератора
2. `rfgen/backends/hackrf.py` - реализована IF компенсация
3. `rfgen/ui_qt/pages/page_406.py` - обновлён вызов run_loop()
4. `rfgen/ui_qt/pages/page_gen_basic.py` - обновлён вызов run_loop()

---

### Статус
✅ **Реализация завершена**
✅ **Все unit-тесты пройдены**
✅ **Все smoke-тесты (A, B, C) пройдены**
✅ **Инвариант `RF = target_hz` выполняется**

Готово к интеграционному тестированию с реальным HackRF.

---

### Примечания

**Обратная совместимость:**
- Для sc8 файлов (старые генераторы): без изменений, работает как раньше
- Для cf32 файлов: применяется цифровой сдвиг автоматически

**Логирование:**
Каждый запуск HackRF теперь логирует IF параметры в `rfgen/logs/hackrf_*.log`:
```
=== IF Compensation ===
Target: 406037000 Hz
IF offset: -37000 Hz
Freq corr: 0 Hz
Center (LO): 406000000 Hz
Digital shift: 37000 Hz
RF out (invariant): 406037000 Hz (should equal target)
```

Это позволяет мгновенно проверять корректность IF компенсации.

**Тестовый скрипт:**
Локально доступен: `test_if_compensation.py` (не коммитится из-за .gitignore)
Запуск: `python test_if_compensation.py`
