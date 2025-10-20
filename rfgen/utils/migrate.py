"""Модуль для миграции старых профилей из корневой папки в пакет."""
from pathlib import Path
from .paths import pkg_root, profiles_dir


def migrate_legacy_profiles() -> int:
    """Переносит профили из старого <repo_root>/profiles/ в новый rfgen/profiles/.

    Returns:
        Количество перенесённых файлов.
    """
    moved = 0
    legacy = pkg_root().parent / "profiles"  # <repo_root>/profiles/

    if not legacy.exists():
        return 0

    target = profiles_dir()

    for f in legacy.glob("*.json"):
        dst = target / f.name
        # Если файл уже существует, добавим суффикс _migrated
        if dst.exists():
            dst = target / (f.stem + "_migrated.json")

        # Перемещаем файл
        f.replace(dst)
        moved += 1

    # Пытаемся удалить старый каталог, если он пустой
    try:
        legacy.rmdir()
    except OSError:
        pass  # Каталог не пустой или есть другие проблемы

    return moved
