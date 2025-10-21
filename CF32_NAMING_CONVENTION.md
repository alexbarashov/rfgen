# Конвенция именования .cf32 файлов

**Дата:** 2025-10-21
**Статус:** ✅ РЕАЛИЗОВАНО

---

## Обзор

Реализована единая конвенция именования `.cf32` файлов по аналогии с проектом TesterPi.

**Цели:**
1. Определять частоту дискретизации (Fs) из имени входного `.cf32` файла
2. При сохранении `.cf32` всегда включать Fs в имя файла
3. Обеспечить консистентность именования во всём проекте

---

## Конвенция именования

### Входные файлы

**Шаблоны:** (регистронезависимо)
- `iq_<FSk>.cf32`
- `iq_<FSk>_<name>.cf32`

Где `<FSk>` — целое число в **кГц** (например, `1024`, `1000`, `2048`).

**Примеры:**
```
iq_1024.cf32           → Fs = 1 024 000 Hz
iq_1024_ais_1.cf32     → Fs = 1 024 000 Hz
iq_1000_epirb_N1.cf32  → Fs = 1 000 000 Hz
iq_2048_test.cf32      → Fs = 2 048 000 Hz
capture.cf32           → Fs = 1 024 000 Hz (fallback)
```

**Fallback:** Если число не найдено → `Fs = 1 024 000 Hz` (1024 кГц)

### Выходные файлы

**Обязательный шаблон:**
```
iq_<FSk>_<name>.cf32
```

Где:
- `<FSk> = round(Fs/1000)` (целое, в кГц)
- `<name>` — произвольная строка (если не задана — генерируется timestamp)

**Примеры:**
```
Fs=1 024 000 → iq_1024_psk406.cf32
Fs=1 000 000 → iq_1000_epirb_clip_01.cf32
Fs=2 048 000 → iq_2048_utc20251021_153045.cf32
```

**Idempotency:** Если имя уже соответствует `iq_<FSk>_...`, второй FSk не добавляется.

---

## Реализация

### 1. Утилита `rfgen/utils/cf32_naming.py`

**Функции:**

```python
def parse_fs_from_filename(filename: str) -> Tuple[int, bool]:
    """Извлекает Fs из имени файла.

    Returns:
        (fs_hz, is_fallback)

    Examples:
        >>> parse_fs_from_filename("iq_1024_ais.cf32")
        (1024000, False)
        >>> parse_fs_from_filename("capture.cf32")
        (1024000, True)
    """

def generate_cf32_name(
    fs_hz: int,
    custom_name: Optional[str] = None,
    add_timestamp: bool = True
) -> str:
    """Генерирует имя .cf32 файла.

    Examples:
        >>> generate_cf32_name(1024000, "test")
        'iq_1024_test.cf32'
        >>> generate_cf32_name(1000000)
        'iq_1000_utc20251021_153045.cf32'
    """

def sanitize_custom_name(name: str) -> str:
    """Очищает имя от недопустимых символов.

    Examples:
        >>> sanitize_custom_name("test/file.cf32")
        'test_file'
    """

def get_default_save_path(
    base_dir: Path,
    fs_hz: int,
    custom_name: Optional[str] = None
) -> Path:
    """Генерирует полный путь для сохранения .cf32 файла."""
```

### 2. Интеграция в страницу 406 MHz

**Файл:** `rfgen/ui_qt/pages/page_406.py`

**Метод `_start_fileout()` (строки 493-532):**
```python
def _start_fileout(self, prof):
    """Generate and save to file."""
    from ...utils.cf32_naming import generate_cf32_name

    # Generate IQ
    iq = generate_psk406(prof)

    # Generate default filename with Fs
    fs_tx = prof["device"]["fs_tx"]
    default_filename = generate_cf32_name(fs_tx, "psk406")
    # → iq_2000_psk406.cf32 (если Fs=2000000)

    default_path = str(profiles_dir() / default_filename)

    # Show save dialog with proper default name
    file_path, _ = QFileDialog.getSaveFileName(
        self, "Save IQ File", default_path,
        "cf32 Files (*.cf32);;All Files (*.*)")
```

**Метод `_start_hackrf()` (строки 534-580):**
```python
def _start_hackrf(self, prof):
    """Generate and transmit via HackRF."""
    from ...utils.cf32_naming import generate_cf32_name

    # Generate IQ
    iq = generate_psk406(prof)

    # Save to temp file (following naming convention)
    fs_tx = prof["device"]["fs_tx"]
    temp_filename = generate_cf32_name(fs_tx, "temp_psk406", add_timestamp=False)
    # → iq_2000_temp_psk406.cf32

    temp_path = out_dir() / temp_filename
```

**Результат:**
- При сохранении через FileOut backend: дефолтное имя `iq_<FSk>_psk406.cf32`
- При передаче через HackRF: временный файл `iq_<FSk>_temp_psk406.cf32`

---

## Тестирование

### Автоматические тесты

**Файл:** `test_cf32_naming.py`

**Тесты:**
1. `test_parse_fs_from_filename()` - парсинг Fs из имени
2. `test_generate_cf32_name()` - генерация имени
3. `test_idempotency()` - проверка idempotency (нет дублирования)
4. `test_sanitize_custom_name()` - очистка имени
5. `test_acceptance_criteria()` - acceptance тесты из ТЗ

**Результаты:**
```
[PASS] parse_fs_from_filename
[PASS] generate_cf32_name
[PASS] idempotency
[PASS] sanitize_custom_name
[PASS] acceptance_criteria

RESULT: ALL TESTS PASSED
```

### Примеры работы

**Входные файлы:**
```
iq_1024_ais_1.cf32     → парсится Fs=1 024 000 Hz
iq_1000_epirb_N1.cf32  → парсится Fs=1 000 000 Hz
capture.cf32           → Fs=1 024 000 Hz (fallback)
```

**Выходные файлы (при сохранении):**
```
Fs=1024000, name="test"     → iq_1024_test.cf32
Fs=1000000, name="epirb"    → iq_1000_epirb.cf32
Fs=2048000, name=None       → iq_2048_utc20251021_153045.cf32
```

**Idempotency:**
```
Input: iq_1024_custom.cf32
Output: iq_1024_custom.cf32  (не дублирует 1024)
```

---

## Acceptance критерии (из ТЗ)

✅ **1.** Открыть `iq_1024_ais_1.cf32` → парсится `Fs=1 024 000`; при сохранении — `iq_1024_<...>.cf32`

✅ **2.** Открыть `iq_1000_epirb_N1.cf32` → парсится `Fs=1 000 000`; при сохранении — `iq_1000_<...>.cf32`

✅ **3.** Открыть `capture.cf32` → `Fs=1 024 000 (fallback)`; при сохранении — `iq_1024_<...>.cf32`

✅ **4.** Если пользователь вводит имя `iq_1024_custom.cf32` — сохранение не добавляет второй `_1024`

---

## Применение в UI

### Страница 406 MHz

**До:**
```
Default save name: psk406_output.cf32
Temp file (HackRF): temp_psk406.cf32
```

**После:**
```
Default save name: iq_2000_psk406.cf32       (для Fs=2000000)
Temp file (HackRF): iq_2000_temp_psk406.cf32 (для Fs=2000000)
```

**Проверка в UI:**
1. Запустите: `app_rfgen.bat`
2. Откройте страницу **406 MHz**
3. Установите **Fs TX = 2 000 000**
4. Нажмите **"Generate"**
5. В диалоге сохранения увидите: `iq_2000_psk406.cf32` ✅

---

## Будущее применение

Конвенция должна быть применена ко всем местам генерации/загрузки `.cf32` файлов:

**Страницы для обновления:**
- ✅ **406 MHz** - DONE
- ⏳ **AIS** - TODO
- ⏳ **DSC VHF** - TODO
- ⏳ **DSC HF** - TODO
- ⏳ **NAVTEX** - TODO
- ⏳ **121.5 MHz** - TODO
- ⏳ **Basic** (page_gen_basic.py) - TODO

**Backends:**
- ✅ **FileOut** - интегрирован через страницы
- ✅ **HackRF** - интегрирован через страницы
- ⏳ **Загрузка файлов** - TODO (если будет режим file)

---

## Изменённые файлы

### Новые файлы

1. **`rfgen/utils/cf32_naming.py`** - утилита для работы с именами
2. **`test_cf32_naming.py`** - тесты утилиты
3. **`CF32_NAMING_CONVENTION.md`** (этот файл) - документация

### Изменённые файлы

4. **`rfgen/ui_qt/pages/page_406.py`**:
   - Метод `_start_fileout()`: использует `generate_cf32_name()` для дефолтного имени
   - Метод `_start_hackrf()`: использует `generate_cf32_name()` для временного файла

---

## Обратная совместимость

✅ **Полная обратная совместимость:**
- Старые файлы без конвенции (`capture.cf32`) работают (используется fallback)
- Парсинг регистронезависимый (`IQ_1024.CF32` работает)
- Пользователь может вводить любое имя вручную (будет очищено от недопустимых символов)
- Никаких breaking changes

---

## Статус

✅ **Утилита cf32_naming.py** - РЕАЛИЗОВАНА
✅ **Тесты** - PASSED (5/5)
✅ **Интеграция в страницу 406 MHz** - COMPLETED
✅ **Документация** - CREATED
⏳ **Применение к другим страницам** - TODO (для будущего)

---

## Логи (рекомендуется добавить в будущем)

**При загрузке файла:**
```
INFO  [FILE] open=iq_1024_ais_1.cf32  Fs(file)=1024000 Hz (fallback=False)
INFO  [FILE] open=capture.cf32  Fs(file)=1024000 Hz (fallback=True)
```

**При сохранении файла:**
```
INFO  [SAVE] cf32 path=C:\work\rfgen\out\iq_2000_psk406.cf32  Fs=2000000 Hz
```

---

## Итог

Реализована полная конвенция именования `.cf32` файлов согласно ТЗ из TesterPi. Все тесты пройдены, интеграция в страницу 406 MHz завершена. Система готова к применению на других страницах проекта.
