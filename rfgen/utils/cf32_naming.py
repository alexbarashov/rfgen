"""Утилиты для работы с именами .cf32 файлов.

Конвенция именования:
- Входные файлы: iq_<FSk>.cf32 или iq_<FSk>_<name>.cf32
- Выходные файлы: всегда iq_<FSk>_<name>.cf32
- FSk = Fs в кГц (целое число)
- Fallback Fs = 1024000 Hz (1024 кГц)
"""

import re
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional


DEFAULT_FS_HZ = 1_024_000  # Fallback Fs (1024 кГц)


def parse_fs_from_filename(filename: str) -> Tuple[int, bool]:
    """Извлекает частоту дискретизации (Fs) из имени файла .cf32.

    Шаблоны:
    - iq_<FSk>.cf32
    - iq_<FSk>_<name>.cf32

    где FSk - целое число в кГц.

    Args:
        filename: Имя файла (с расширением или без)

    Returns:
        (fs_hz, is_fallback) - частота в Гц и флаг fallback

    Examples:
        >>> parse_fs_from_filename("iq_1024.cf32")
        (1024000, False)
        >>> parse_fs_from_filename("iq_1000_epirb.cf32")
        (1000000, False)
        >>> parse_fs_from_filename("capture.cf32")
        (1024000, True)
    """
    # Убираем путь, оставляем только имя файла
    basename = Path(filename).name

    # Regex: iq_<число>(_|.)
    # Ищем первое число после "iq_"
    pattern = r'^iq_(\d+)(?:_|\.)'
    match = re.search(pattern, basename, re.IGNORECASE)

    if match:
        fs_khz = int(match.group(1))
        fs_hz = fs_khz * 1000
        return fs_hz, False

    # Fallback
    return DEFAULT_FS_HZ, True


def generate_cf32_name(
    fs_hz: int,
    custom_name: Optional[str] = None,
    add_timestamp: bool = True
) -> str:
    """Генерирует имя .cf32 файла по конвенции.

    Формат: iq_<FSk>_<name>.cf32

    Args:
        fs_hz: Частота дискретизации в Гц
        custom_name: Пользовательская часть имени (опционально)
        add_timestamp: Добавить timestamp если custom_name не задано

    Returns:
        Имя файла вида iq_<FSk>_<name>.cf32

    Examples:
        >>> generate_cf32_name(1024000, "test")
        'iq_1024_test.cf32'
        >>> generate_cf32_name(1000000)
        'iq_1000_utc20251021_153045.cf32'
    """
    # Fs в кГц (округляем)
    fs_khz = round(fs_hz / 1000)

    # Если custom_name не задано - генерируем timestamp
    if not custom_name:
        if add_timestamp:
            timestamp = datetime.utcnow().strftime("utc%Y%m%d_%H%M%S")
            custom_name = timestamp
        else:
            custom_name = "output"

    # Проверка idempotency: если custom_name уже начинается с iq_<FSk>_
    # то не дублируем
    pattern = rf'^iq_{fs_khz}_'
    if re.match(pattern, custom_name, re.IGNORECASE):
        # Уже есть префикс, используем как есть
        return f"{custom_name}.cf32" if not custom_name.endswith('.cf32') else custom_name

    # Собираем имя
    return f"iq_{fs_khz}_{custom_name}.cf32"


def sanitize_custom_name(name: str) -> str:
    """Очищает пользовательское имя от недопустимых символов.

    Args:
        name: Исходное имя

    Returns:
        Очищенное имя (безопасное для файловой системы)

    Examples:
        >>> sanitize_custom_name("test/file.cf32")
        'test_file'
        >>> sanitize_custom_name("my signal#1")
        'my_signal_1'
    """
    # Убираем расширение .cf32 если есть
    name = name.replace('.cf32', '').replace('.CF32', '')

    # Заменяем недопустимые символы на _
    # Разрешены: буквы, цифры, _, -
    sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)

    # Убираем множественные подчёркивания
    sanitized = re.sub(r'_+', '_', sanitized)

    # Убираем подчёркивания в начале/конце
    sanitized = sanitized.strip('_')

    return sanitized or "output"


def get_default_save_path(
    base_dir: Path,
    fs_hz: int,
    custom_name: Optional[str] = None
) -> Path:
    """Генерирует полный путь для сохранения .cf32 файла.

    Args:
        base_dir: Базовая директория для сохранения
        fs_hz: Частота дискретизации в Гц
        custom_name: Пользовательская часть имени (опционально)

    Returns:
        Полный путь к файлу

    Examples:
        >>> get_default_save_path(Path("/tmp"), 1024000, "test")
        Path('/tmp/iq_1024_test.cf32')
    """
    filename = generate_cf32_name(fs_hz, custom_name)
    return base_dir / filename
