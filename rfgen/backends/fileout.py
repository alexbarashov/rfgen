from pathlib import Path
from ..core.recording import save_cf32, save_sc8
from ..utils.paths import out_dir as _default_out_dir

class FileOutBackend:
    def __init__(self, out_dir: Path = None):
        """Инициализация backend для вывода в файл.

        Args:
            out_dir: Каталог для сохранения файлов. Если None, используется rfgen/out/
        """
        self.out_dir = Path(out_dir) if out_dir else _default_out_dir()
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def write_cf32(self, name: str, iq):
        path = self.out_dir / f"{name}.cf32"
        save_cf32(path, iq)
        return str(path)

    def write_sc8(self, name: str, iq):
        path = self.out_dir / f"{name}.sc8"
        save_sc8(path, iq)
        return str(path)
