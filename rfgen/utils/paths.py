"""Централизованное управление путями проекта rfgen."""
from pathlib import Path


def pkg_root() -> Path:
    """Возвращает корневой каталог пакета rfgen/.

    Любой модуль внутри пакета: rfgen/<...>/<this_file>.py
    → parents[1] == rfgen/
    """
    return Path(__file__).resolve().parents[1]


def profiles_dir() -> Path:
    """Возвращает каталог для профилей: rfgen/profiles/."""
    p = pkg_root() / "profiles"
    p.mkdir(parents=True, exist_ok=True)
    return p


def out_dir() -> Path:
    """Возвращает каталог для выходных файлов (IQ): rfgen/out/."""
    p = pkg_root() / "out"
    p.mkdir(parents=True, exist_ok=True)
    return p


def logs_dir() -> Path:
    """Возвращает каталог для логов: rfgen/logs/."""
    p = pkg_root() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p
