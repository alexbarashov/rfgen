"""Работа с профилями: валидация, дефолты, загрузка/сохранение."""
import json
from pathlib import Path
from typing import Any, Optional

PROFILE_SCHEMA_VERSION = 1


def defaults() -> dict[str, Any]:
    """Возвращает дефолтные значения для всех блоков профиля."""
    return {
        "schema": PROFILE_SCHEMA_VERSION,
        "name": "Unnamed Profile",
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
            "repeat": 1,
            "gap_s": 0.0,
            "duration_s": 1.0
        },
        "device": {
            "backend": "hackrf",
            "fs_tx": 2000000,
            "tx_gain_db": 30,
            "pa": False,
            "target_hz": 162025000,
            "if_offset_hz": 0,
            "freq_corr_hz": 0
        },
        "_meta": {
            "created_utc": "",
            "notes": ""
        }
    }


def validate_profile(p: dict) -> tuple[bool, str]:
    """Валидация профиля.

    Returns:
        (True, "") если профиль валиден
        (False, "error message") если есть ошибки
    """
    if not isinstance(p, dict):
        return False, "Profile must be a dictionary"

    # Проверяем обязательные блоки
    required_blocks = ["device", "modulation", "pattern", "schedule"]
    for block in required_blocks:
        if block not in p:
            return False, f"Missing required block: '{block}'"

    # Валидация device
    device = p.get("device", {})
    if "backend" not in device:
        return False, "Missing device.backend"

    backend = device.get("backend")
    if backend not in ("hackrf", "fileout", "pluto"):
        return False, f"Invalid backend: '{backend}'"

    # Валидация численных параметров device
    try:
        fs_tx = int(device.get("fs_tx", 0))
        if not (100_000 <= fs_tx <= 20_000_000):
            return False, f"fs_tx must be 100kHz-20MHz, got {fs_tx}"

        tx_gain = int(device.get("tx_gain_db", 0))
        if not (0 <= tx_gain <= 47):
            return False, f"tx_gain_db must be 0-47, got {tx_gain}"

        target_hz = int(device.get("target_hz", 0))
        if not (0 <= target_hz <= 7_250_000_000):
            return False, f"target_hz must be 0-7.25GHz, got {target_hz}"
    except (ValueError, TypeError) as e:
        return False, f"Invalid numeric value in device: {e}"

    # Валидация modulation type
    mod = p.get("modulation", {})
    mod_type = mod.get("type", "None")
    if mod_type not in ("None", "AM", "FM", "PM"):
        return False, f"Invalid modulation type: '{mod_type}'"

    # Валидация pattern type
    pattern = p.get("pattern", {})
    pattern_type = pattern.get("type", "Tone")
    valid_patterns = ("Tone", "Sweep", "Noise", "FF00", "F0F0", "3333", "5555")
    if pattern_type not in valid_patterns:
        return False, f"Invalid pattern type: '{pattern_type}'"

    # Валидация standard
    standard = p.get("standard", "basic")
    valid_standards = ("basic", "ais", "c406", "dsc_vhf", "dsc_hf", "navtex", "121")
    if standard not in valid_standards:
        return False, f"Invalid standard: '{standard}'"

    return True, ""


def apply_defaults(p: dict) -> dict:
    """Применяет дефолтные значения к профилю (заполняет пропущенные поля).

    Args:
        p: Исходный профиль (может быть неполным)

    Returns:
        Профиль с заполненными дефолтами
    """
    result = defaults()

    # Рекурсивно обновляем вложенные словари
    def deep_update(base: dict, update: dict) -> dict:
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                base[key] = deep_update(base[key].copy(), value)
            else:
                base[key] = value
        return base

    return deep_update(result, p)


def load_json(path: Path) -> Optional[dict]:
    """Загружает JSON из файла.

    Returns:
        dict если успешно, None при ошибке
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def save_json(path: Path, data: dict) -> bool:
    """Сохраняет словарь в JSON файл.

    Returns:
        True если успешно, False при ошибке
    """
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def migrate_legacy_profile(p: dict) -> dict:
    """Мигрирует старый профиль в новый формат.

    Старые профили могут не иметь:
    - поля "schema"
    - блока "standard" и "standard_params"
    - блока "_meta"
    - некоторых полей в device/modulation/pattern/schedule
    """
    # Если уже есть schema и он актуальный - ничего не делаем
    if p.get("schema") == PROFILE_SCHEMA_VERSION:
        return p

    # Создаём новый профиль на основе дефолтов
    result = defaults()

    # Копируем имя если есть
    if "name" in p:
        result["name"] = p["name"]

    # Определяем standard из контекста (пока всегда basic для старых)
    result["standard"] = p.get("standard", "basic")

    # Копируем блоки если есть
    for block in ("device", "modulation", "pattern", "schedule"):
        if block in p:
            for key, value in p[block].items():
                if key in result[block]:
                    result[block][key] = value

    # Добавляем schema
    result["schema"] = PROFILE_SCHEMA_VERSION

    return result
