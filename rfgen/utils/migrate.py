"""Миграция профилей из старых мест в rfgen/profiles/."""
import shutil
from pathlib import Path
from typing import Any, Optional
from .paths import pkg_root, profiles_dir
from .profile_io import load_json, save_json, migrate_legacy_profile


def get_legacy_profiles_dir() -> Optional[Path]:
    """Возвращает путь к старой папке profiles/ в корне репо.

    Returns:
        Path если найдена, None если нет
    """
    # pkg_root() это rfgen/
    # Корень репо на уровень выше
    repo_root = pkg_root().parent
    legacy_dir = repo_root / "profiles"

    if legacy_dir.exists() and legacy_dir.is_dir():
        return legacy_dir
    return None


def migrate_legacy_profiles(dry_run: bool = False) -> dict[str, Any]:
    """Переносит профили из корневой папки profiles/ в rfgen/profiles/.

    Алгоритм:
    1. Ищем <repo_root>/profiles/*.json
    2. Для каждого файла:
       - Загружаем JSON
       - Мигрируем формат если нужно
       - Копируем в rfgen/profiles/
       - При конфликте имён добавляем суффикс _migrated
    3. Старые файлы НЕ удаляем (пользователь сам решит)

    Args:
        dry_run: Если True, только показывает что будет сделано

    Returns:
        dict с результатами миграции:
        {
            "found": int,           # Найдено профилей
            "migrated": int,        # Успешно перенесено
            "skipped": int,         # Пропущено (уже есть)
            "errors": list[str],    # Ошибки
            "files": list[str]      # Перенесённые файлы
        }
    """
    result = {
        "found": 0,
        "migrated": 0,
        "skipped": 0,
        "errors": [],
        "files": []
    }

    legacy_dir = get_legacy_profiles_dir()
    if not legacy_dir:
        result["errors"].append("Legacy profiles directory not found")
        return result

    # Ищем все .json файлы
    json_files = list(legacy_dir.glob("*.json"))
    result["found"] = len(json_files)

    if result["found"] == 0:
        return result

    target_dir = profiles_dir()

    for json_file in json_files:
        try:
            # Загружаем
            data = load_json(json_file)
            if data is None:
                result["errors"].append(f"Failed to load: {json_file.name}")
                continue

            # Мигрируем формат
            migrated_data = migrate_legacy_profile(data)

            # Определяем целевое имя файла
            target_name = json_file.name
            target_path = target_dir / target_name

            # Проверяем конфликт
            if target_path.exists():
                # Добавляем суффикс
                stem = target_path.stem
                target_path = target_dir / f"{stem}_migrated.json"

                # Если и это занято - пропускаем
                if target_path.exists():
                    result["skipped"] += 1
                    result["errors"].append(f"Skipped (already exists): {json_file.name}")
                    continue

            # Сохраняем
            if not dry_run:
                if save_json(target_path, migrated_data):
                    result["migrated"] += 1
                    result["files"].append(target_path.name)
                else:
                    result["errors"].append(f"Failed to save: {target_path.name}")
            else:
                result["migrated"] += 1
                result["files"].append(f"[DRY RUN] {target_path.name}")

        except Exception as e:
            result["errors"].append(f"Error processing {json_file.name}: {e}")

    return result


def cleanup_legacy_profiles(confirm: bool = False) -> bool:
    """Удаляет старую папку profiles/ после миграции.

    ОСТОРОЖНО: удаляет всю папку со всем содержимым!

    Args:
        confirm: Должно быть True для реального удаления

    Returns:
        True если удалено, False если нет
    """
    if not confirm:
        return False

    legacy_dir = get_legacy_profiles_dir()
    if not legacy_dir:
        return False

    try:
        shutil.rmtree(legacy_dir)
        return True
    except Exception:
        return False
