import subprocess
import os
import signal
import time
import datetime
from pathlib import Path
import numpy as np
from ..utils.paths import logs_dir

CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)


# ==================== Утилиты для работы с IQ ====================

def _read_cf32(path: Path) -> np.ndarray:
    """Чтение cf32 IQ-файла (interleaved float32)."""
    raw = np.fromfile(str(path), dtype=np.float32)
    if raw.size % 2 != 0:
        raise ValueError(f"cf32 file has odd number of floats: {path}")
    i = raw[0::2]
    q = raw[1::2]
    return (i + 1j * q).astype(np.complex64)


def _iq_cf32_to_sc8(iq: np.ndarray, amp_scale: float = 0.95) -> bytes:
    """
    Конверсия IQ cf32 → sc8 (interleaved int8).

    Параметры:
    - iq: complex64 массив
    - amp_scale: масштаб амплитуды (0..1), по умолчанию 0.95

    Возвращает: bytes (interleaved int8: I, Q, I, Q, ...)
    """
    if iq.dtype != np.complex64:
        iq = iq.astype(np.complex64, copy=False)

    # Нормализация к ±1.0
    peak = np.max(np.abs(iq)) if iq.size > 0 else 1.0
    if peak > 1.0:
        iq = iq / peak

    # Масштабирование
    iq = iq * amp_scale

    # Квантование в int8 (±127)
    i8 = np.empty(iq.size * 2, dtype=np.int8)
    i = np.clip(np.round(iq.real * 127.0), -127, 127).astype(np.int8)
    q = np.clip(np.round(iq.imag * 127.0), -127, 127).astype(np.int8)
    i8[0::2] = i
    i8[1::2] = q

    return i8.tobytes()


def _calc_metrics(iq: np.ndarray) -> dict:
    """Расчёт метрик IQ-буфера (RMS, peak)."""
    if iq.size == 0:
        return {"rms": 0.0, "peak": 0.0}

    peak = float(np.max(np.abs(iq)))
    rms = float(np.sqrt(np.mean(np.abs(iq) ** 2)))

    return {"rms": rms, "peak": peak}


class HackRFTx:
    def __init__(self, exe: str = "hackrf_transfer"):
        self.exe = exe
        self.proc: subprocess.Popen | None = None
        self.pid: int | None = None
        self.log_path: Path | None = None
        self.cmdline: list[str] | None = None

    def _create_log(self) -> Path:
        """Создаём путь к лог-файлу и инициализируем его."""
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = logs_dir() / f"hackrf_{ts}.log"
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] log started\n")
                f.flush()
        except Exception:
            pass
        return path

    def _log(self, message: str):
        """Пишем сообщение в лог-файл (отдельное открытие каждый раз)."""
        if not self.log_path:
            return
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(message + "\n")
                f.flush()
        except Exception:
            pass

    def run_loop(self, iq_path: Path, fs_tx: int, center_hz: int, tx_gain_db: int, pa_enabled: bool = False):
        """
        Стартуем hackrf_transfer в режиме loop (-R).

        Параметры:
        - iq_path: путь к IQ-файлу (cf32 или sc8)
        - fs_tx: частота дискретизации TX (Гц)
        - center_hz: центральная частота (Гц)
        - tx_gain_db: TX gain (dB), 0..47
        - pa_enabled: включить PA (флаг -a 1)

        Процесс:
        1. Определяем формат файла (cf32 или sc8)
        2. Если cf32: читаем, рассчитываем метрики, конвертируем в sc8
        3. Если sc8: используем напрямую (обратная совместимость)
        4. Запускаем hackrf_transfer с флагом -a 1 (если pa_enabled)
        5. Логируем всё в лог-файл
        """
        if self.is_running():
            raise RuntimeError("HackRF already running")

        if not iq_path.exists():
            raise FileNotFoundError(f"IQ file not found: {iq_path}")

        # 1. Определяем формат
        is_cf32 = iq_path.suffix.lower() in (".cf32", ".iq")
        metrics = {"rms": 0.0, "peak": 0.0}  # по умолчанию

        if is_cf32:
            # 2A. Читаем cf32 файл
            iq_cf32 = _read_cf32(iq_path)

            # Рассчитываем метрики
            metrics = _calc_metrics(iq_cf32)

            # Конвертируем в sc8
            sc8_bytes = _iq_cf32_to_sc8(iq_cf32, amp_scale=0.95)

            # Сохраняем sc8 во временный файл (рядом с cf32)
            sc8_path = iq_path.with_suffix(".sc8")
            with open(sc8_path, "wb") as f:
                f.write(sc8_bytes)
        else:
            # 2B. Используем sc8 напрямую (обратная совместимость)
            sc8_path = iq_path
            sc8_bytes = sc8_path.read_bytes()

        # 5. Формируем команду для hackrf_transfer
        cmd = [
            self.exe, "-t", str(sc8_path),
            "-f", str(int(center_hz)),
            "-s", str(int(fs_tx)),
            "-x", str(int(tx_gain_db)),
        ]

        # Добавляем флаг PA если включён
        if pa_enabled:
            cmd += ["-a", "1"]

        # Режим loop
        cmd += ["-R"]

        self.cmdline = cmd

        # 6. Создаём лог-файл
        self.log_path = self._create_log()

        # Создаём отдельный файл для вывода hackrf_transfer
        # Открываем его один раз, передаём процессу, и сразу закрываем в Python
        output_path = self.log_path.with_suffix('.output.txt')
        output_fh = open(output_path, 'w', encoding='utf-8')

        # ЭКСПЕРИМЕНТ: НЕ используем CREATE_NEW_PROCESS_GROUP
        # Это флаг может делать процесс неубиваемым на Windows
        self.proc = subprocess.Popen(
            cmd,
            stdout=output_fh,
            stderr=subprocess.STDOUT
        )
        self.pid = self.proc.pid

        # КРИТИЧНО: Закрываем handle СРАЗУ после создания процесса!
        # Процесс уже унаследовал handle, но Python больше не держит его
        output_fh.close()

        # 7. Логируем заголовок с метриками
        self._log(f"CMD: {' '.join(cmd)}")
        self._log(f"PID: {self.pid}")
        self._log(f"INPUT: {iq_path} ({'cf32' if is_cf32 else 'sc8'})")
        self._log(f"IQ_SC8: {sc8_path}")
        self._log(f"OUTPUT: {output_path}")
        self._log("")
        self._log(f"=== Metrics ===")
        if is_cf32:
            self._log(f"CF32 samples: {iq_cf32.size}")
        self._log(f"SC8 bytes: {len(sc8_bytes)}")
        self._log(f"RMS: {metrics['rms']:.6f}")
        self._log(f"Peak: {metrics['peak']:.6f}")
        self._log(f"PA enabled: {pa_enabled}")
        self._log(f"Center: {center_hz} Hz")
        self._log(f"Fs TX: {fs_tx} Hz")
        self._log(f"TX Gain: {tx_gain_db} dB")
        self._log("")

        # Валидация: предупреждение если peak близок к нулю (только для cf32)
        if is_cf32 and metrics['peak'] < 0.001:
            self._log("WARNING: Peak level very low (< 0.001)!")
            print(f"[HackRF] WARNING: Peak level very low: {metrics['peak']:.6f}")

        return self.proc

    def is_running(self) -> bool:
        return self.proc is not None and (self.proc.poll() is None)

    def stop(self, timeout_sec: float = 1.0):
        """Graceful CTRL_BREAK (Windows) / terminate → wait → force kill; логируем все шаги."""
        print(f"[DEBUG HackRF] stop() called for PID {self.pid}")  # DEBUG

        if not self.proc:
            print("[DEBUG HackRF] No process to stop")  # DEBUG
            return

        self._log(f"\n[stop] stopping PID {self.pid}")

        # БЕЗ CREATE_NEW_PROCESS_GROUP можно сразу использовать terminate()
        self._log(f"[stop] sending terminate to PID {self.pid}")

        try:
            self.proc.terminate()
        except Exception:
            pass

        # Ждём немного (terminate обычно работает быстро)
        t0 = time.time()
        while self.is_running() and (time.time() - t0) < 0.5:
            time.sleep(0.05)

        # 3) Форс-килл при необходимости
        if self.is_running():
            self._log("[stop] still running → kill()")
            try:
                self.proc.kill()
            except Exception:
                pass

        rc = None
        try:
            rc = self.proc.wait(timeout=1.0)
        except Exception:
            pass

        # КРИТИЧЕСКАЯ ПРОВЕРКА: Действительно ли процесс завершён?
        # Проверяем через tasklist, т.к. wait() может вернуться, но процесс останется зомби
        process_in_tasklist = False
        if os.name == "nt":
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {self.pid}", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                process_in_tasklist = "hackrf_transfer.exe" in result.stdout
            except Exception:
                pass

        if process_in_tasklist or self.is_running():
            print(f"[DEBUG HackRF] Process still alive after wait()! Using taskkill...")  # DEBUG
            self._log(f"[stop] process still in tasklist (zombie), using taskkill")

            # Финальный метод: taskkill через subprocess
            if os.name == "nt":
                try:
                    result = subprocess.run(
                        ["taskkill", "/PID", str(self.pid), "/F", "/T"],
                        capture_output=True,
                        text=True,
                        timeout=3
                    )
                    self._log(f"[stop] taskkill output: {result.stdout.strip()}")
                    if result.stderr:
                        self._log(f"[stop] taskkill errors: {result.stderr.strip()}")
                    self._log(f"[stop] taskkill returncode: {result.returncode}")

                    # Ждём дольше после taskkill - Windows может быть медленным
                    time.sleep(1.0)

                    # Проверяем снова
                    result2 = subprocess.run(
                        ["tasklist", "/FI", f"PID eq {self.pid}", "/NH"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    still_there = "hackrf_transfer.exe" in result2.stdout
                    if still_there:
                        self._log(f"[stop] WARNING: Process STILL in tasklist after taskkill!")
                        print(f"[DEBUG HackRF] Process STILL there after taskkill!")  # DEBUG
                    else:
                        self._log(f"[stop] Process successfully killed by taskkill")
                except Exception as e:
                    print(f"[DEBUG HackRF] taskkill failed: {e}")  # DEBUG
                    self._log(f"[stop] taskkill exception: {e}")

        self._log(f"[stop] stopped, returncode={rc}")

        print(f"[DEBUG HackRF] Process stopped, returncode={rc}")  # DEBUG
        print(f"[DEBUG HackRF] is_running() = {self.is_running()}")  # DEBUG

        self.proc = None
        self.pid = None

        print("[DEBUG HackRF] stop() finished")  # DEBUG
