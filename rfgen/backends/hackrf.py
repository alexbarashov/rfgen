import subprocess
import os
import signal
import time
import datetime
from pathlib import Path
from ..utils.paths import logs_dir

CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)


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

    def run_loop(self, iq_path: Path, fs_tx: int, center_hz: int, tx_gain_db: int):
        """Стартуем hackrf_transfer в -R. Вывод → лог. Храним PID/cmdline."""
        if self.is_running():
            raise RuntimeError("HackRF already running")

        cmd = [
            self.exe, "-t", str(iq_path),
            "-f", str(int(center_hz)),
            "-s", str(int(fs_tx)),
            "-x", str(int(tx_gain_db)),
            "-R"
        ]
        self.cmdline = cmd

        # Создаём лог-файл (без хранения handle!)
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

        # Логируем заголовок
        self._log(f"CMD: {' '.join(cmd)}")
        self._log(f"PID: {self.pid}")
        self._log(f"IQ: {iq_path}")
        self._log(f"OUTPUT: {output_path}")
        self._log("")

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
