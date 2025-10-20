from pathlib import Path
import subprocess, os, shutil

class HackRFTx:
    def __init__(self, exe: str = None):
        self.exe = exe or shutil.which("hackrf_transfer") or "hackrf_transfer"
        self.proc = None

    def run_loop(self, iq_path: Path, fs_tx: int, center_hz: int, tx_gain_db: int):
        iq_path = Path(iq_path)
        cmd = [self.exe, "-t", str(iq_path),
               "-f", str(int(center_hz)),
               "-s", str(int(fs_tx)),
               "-x", str(int(tx_gain_db)),
               "-R"]
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        self.proc = subprocess.Popen(cmd, creationflags=flags)
        return self.proc

    def is_running(self) -> bool:
        return (self.proc is not None) and (self.proc.poll() is None)


    def stop(self):
        if not self.proc: return
        try:
            if os.name == "nt":
                self.proc.send_signal(signal.CTRL_BREAK_EVENT)
            self.proc.terminate()
            self.proc.wait(timeout=1.0)
        except Exception:
            try: self.proc.kill()
            except Exception: pass
        self.proc = None


