# Добавлен переключатель режимов ввода на странице 406 MHz

**Дата:** 2025-10-21
**Статус:** ✅ РЕАЛИЗОВАНО И ПРОТЕСТИРОВАНО

---

## Обзор

Добавлен переключатель между двумя режимами ввода сообщения на странице 406 MHz:
1. **Direct HEX** (по умолчанию) - прямой ввод HEX сообщения
2. **Message Builder** - генерация HEX из beacon_id/lat/lon (для будущей реализации)

---

## Мотивация

**Текущее поведение:**
Генератор PSK-406 всегда использует статическое HEX сообщение из поля "HEX Message", игнорируя поля:
- Message Type
- Beacon ID
- Latitude
- Longitude
- FEC настройки
- Interleave

**Требование:**
Предусмотреть в UI выбор между:
- Использованием готового HEX (текущее поведение, по умолчанию)
- Генерацией HEX из структурированных полей (для будущей реализации)

---

## Реализация

### 1. Добавлены Radio Buttons для выбора режима

**Файл:** `rfgen/ui_qt/pages/page_406.py`

**Строки 78-93:** Добавлен переключатель режимов:
```python
# Mode selection (Radio buttons)
mode_layout = QHBoxLayout()
mode_label = QLabel("Input Mode:")
self.radio_hex = QRadioButton("Direct HEX")
self.radio_builder = QRadioButton("Message Builder")
self.radio_hex.setChecked(True)  # Default: Direct HEX

self.mode_group = QButtonGroup(self)
self.mode_group.addButton(self.radio_hex, 0)
self.mode_group.addButton(self.radio_builder, 1)
```

### 2. Логика включения/отключения полей

**Строки 229-241:** Метод `_on_mode_changed()`:
```python
def _on_mode_changed(self):
    """Handle mode switching between Direct HEX and Message Builder."""
    is_hex_mode = self.radio_hex.isChecked()

    # Direct HEX mode: enable hex_message, disable builder fields
    # Message Builder mode: disable hex_message, enable builder fields
    self.hex_message.setEnabled(is_hex_mode)
    self.combo_msg_type.setEnabled(not is_hex_mode)
    self.beacon_id.setEnabled(not is_hex_mode)
    self.lat.setEnabled(not is_hex_mode)
    self.lon.setEnabled(not is_hex_mode)

    # Trigger autosave when mode changes
    self._autosave_to_default()
```

**Поведение:**
- **Direct HEX режим**: активно только поле "HEX Message"
- **Message Builder режим**: активны поля "Message Type", "Beacon ID", "Latitude", "Longitude"

### 3. Сохранение/загрузка режима

**Строка 334:** В `_collect_profile()` добавлено поле `input_mode`:
```python
"standard_params": {
    "input_mode": "hex" if self.radio_hex.isChecked() else "builder",
    ...
}
```

**Строки 436-442:** В `_apply_profile_to_form()` добавлена загрузка режима:
```python
# Input mode (hex or builder)
input_mode = str(sp.get("input_mode", "hex"))
if input_mode == "hex":
    self.radio_hex.setChecked(True)
else:
    self.radio_builder.setChecked(True)
```

**Строка 263:** В `_load_default_profile()` дефолтный режим:
```python
default_profile["standard_params"] = {
    "input_mode": "hex",  # Default to Direct HEX mode
    ...
}
```

### 4. Интеграция с автосохранением

**Строки 224-227:** Подключение сигналов после создания таймера:
```python
# Connect mode switch and set initial state (after timer is created)
self.radio_hex.toggled.connect(self._on_mode_changed)
self.radio_builder.toggled.connect(self._on_mode_changed)
self._on_mode_changed()  # Set initial field states
```

Режим автоматически сохраняется в `default.json` при переключении.

---

## Тестирование

### Автоматический тест

**Тест:** Переключение режимов и состояние полей
```bash
python -c "from rfgen.ui_qt.pages.page_406 import Page406; ..."
```

**Результаты:**
```
[1] Initial state check:
    Direct HEX selected: True
    HEX field enabled: True
    Beacon ID enabled: False
    [OK] Initial state correct (Direct HEX mode)

[2] Switch to Message Builder mode:
    Message Builder selected: True
    HEX field enabled: False
    Beacon ID enabled: True
    [OK] Builder mode correct

[3] Switch back to Direct HEX mode:
    HEX field enabled: True
    Beacon ID enabled: False
    [OK] HEX mode correct

[SUCCESS] All mode switching tests passed!
```

### Ручное тестирование

**Проверьте в UI:**
1. Запустите: `app_rfgen.bat`
2. Откройте страницу **406 MHz**
3. **По умолчанию:**
   - ✅ Выбран "Direct HEX"
   - ✅ Поле "HEX Message" активно
   - ✅ Поля "Message Type", "Beacon ID", "Lat", "Lon" неактивны (серые)

4. **Переключите на "Message Builder":**
   - ✅ Поле "HEX Message" стало неактивным
   - ✅ Поля "Message Type", "Beacon ID", "Lat", "Lon" стали активными

5. **Сохраните профиль** и **загрузите обратно:**
   - ✅ Режим восстанавливается корректно

---

## Изменённые файлы

**`rfgen/ui_qt/pages/page_406.py`:**
- Добавлен импорт `QRadioButton`, `QButtonGroup`
- Добавлены виджеты переключателя режимов
- Добавлен метод `_on_mode_changed()`
- Обновлён `_collect_profile()` (сохранение режима)
- Обновлён `_apply_profile_to_form()` (загрузка режима)
- Обновлён `_load_default_profile()` (дефолтный режим)
- Исправлен порядок инициализации (сигналы подключаются после создания таймера)

---

## Текущее поведение

### Direct HEX Mode (по умолчанию)
- Используется HEX сообщение напрямую из поля "HEX Message"
- Поля "Message Type", "Beacon ID", "Lat", "Lon" неактивны
- Генератор `generate_psk406()` получает `hex_message` из профиля

### Message Builder Mode (для будущей реализации)
- Поля "Message Type", "Beacon ID", "Lat", "Lon" активны
- Поле "HEX Message" неактивно
- **ПРИМЕЧАНИЕ:** Генерация HEX из beacon_id/lat/lon пока НЕ реализована
- Генератору всё ещё передаётся значение из поля "HEX Message"

---

## Следующие шаги (опционально)

### Для полной реализации Message Builder Mode:

1. **Создать функцию генерации HEX сообщения:**
   - `rfgen/standards/psk406.py`: добавить функцию `build_406_message(msg_type, beacon_id, lat, lon)`
   - Поддержка всех типов сообщений:
     - Standard Location (Hex ID)
     - User Location (GPS)
     - Test Message
     - BPSK Pattern (Debug)

2. **Обновить генератор:**
   - В `generate_psk406()` проверять `input_mode`
   - Если `input_mode == "builder"` → вызвать `build_406_message()`
   - Если `input_mode == "hex"` → использовать `hex_message` напрямую

3. **Добавить FEC и интерлив:**
   - Реализовать BCH кодирование
   - Реализовать интерлив (если `interleave == True`)

---

## Обратная совместимость

✅ **Полная обратная совместимость:**
- Старые профили без поля `input_mode` работают (дефолт: "hex")
- Существующее поведение (Direct HEX) сохранено как дефолтное
- Никаких breaking changes

---

## Статус

✅ **UI переключатель** - РЕАЛИЗОВАН
✅ **Логика enable/disable полей** - РЕАЛИЗОВАНА
✅ **Сохранение/загрузка режима** - РЕАЛИЗОВАНО
✅ **Автосохранение** - РАБОТАЕТ
✅ **Тестирование** - ПРОЙДЕНО
⏳ **Генерация HEX из beacon_id/lat/lon** - НЕ РЕАЛИЗОВАНО (для будущего)
