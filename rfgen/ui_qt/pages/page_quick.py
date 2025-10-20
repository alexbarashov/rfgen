from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout, QPushButton,
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox,
    QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt
from pathlib import Path
import json, datetime

from ...core.wave_engine import build_iq, build_cw
from ...backends.fileout import FileOutBackend
from ...backends.hackrf import HackRFTx
from ...utils.paths import profiles_dir, out_dir

class PageQuick(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hrf = None  # HackRF process handle wrapper

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)

        # Device group
        dev_group = QGroupBox("Device")
        dev_form = QFormLayout(dev_group)
        self.combo_backend = QComboBox()
        self.combo_backend.addItems(["hackrf", "fileout"])
        self.fs_tx = QSpinBox(); self.fs_tx.setRange(200_000, 20_000_000); self.fs_tx.setSingleStep(100_000); self.fs_tx.setValue(2_000_000)
        self.tx_gain = QSpinBox(); self.tx_gain.setRange(0, 60); self.tx_gain.setValue(30)
        self.pa_enable = QCheckBox("Enable PA")
        dev_form.addRow("Backend", self.combo_backend)
        dev_form.addRow("Fs TX (S/s)", self.fs_tx)
        dev_form.addRow("TX Gain (dB)", self.tx_gain)
        dev_form.addRow("", self.pa_enable)

        # Radio group
        rf_group = QGroupBox("Radio")
        rf_form = QFormLayout(rf_group)
        self.target_hz = QLineEdit("162025000")
        self.if_offset_hz = QLineEdit("0")
        self.freq_corr_hz = QLineEdit("0")
        rf_form.addRow("Target (Hz)", self.target_hz)
        rf_form.addRow("IF offset (Hz)", self.if_offset_hz)
        rf_form.addRow("Freq corr (Hz)", self.freq_corr_hz)

        # Modulation group
        mod_group = QGroupBox("Modulation")
        mod_form = QFormLayout(mod_group)
        self.combo_mod = QComboBox(); self.combo_mod.addItems(["None", "FM", "PM", "AM"])
        self.deviation = QSpinBox(); self.deviation.setRange(0, 200_000); self.deviation.setValue(5000)
        self.pm_index = QDoubleSpinBox(); self.pm_index.setRange(0.0, 10.0); self.pm_index.setSingleStep(0.05); self.pm_index.setValue(1.0)
        self.am_depth = QDoubleSpinBox(); self.am_depth.setRange(0.0, 1.0); self.am_depth.setSingleStep(0.05); self.am_depth.setValue(0.5)
        mod_form.addRow("Type", self.combo_mod)
        mod_form.addRow("FM deviation (Hz)", self.deviation)
        mod_form.addRow("PM index (rad)", self.pm_index)
        mod_form.addRow("AM depth (0..1)", self.am_depth)

        # Pattern group
        pat_group = QGroupBox("Pattern")
        pat_form = QFormLayout(pat_group)
        self.combo_pat = QComboBox(); self.combo_pat.addItems(["Tone", "Sweep", "FF00", "F0F0", "3333", "5555", "Noise"])
        self.tone_hz = QSpinBox(); self.tone_hz.setRange(1, 100_000); self.tone_hz.setValue(1000)
        self.bitrate = QSpinBox(); self.bitrate.setRange(10, 1_000_000); self.bitrate.setValue(9600)
        pat_form.addRow("Type", self.combo_pat)
        pat_form.addRow("Tone Freq (Hz)", self.tone_hz)
        pat_form.addRow("Bitrate (bps)", self.bitrate)

        # Schedule group
        sched_group = QGroupBox("Schedule")
        sched_form = QFormLayout(sched_group)
        self.loop = QCheckBox("Loop forever"); self.loop.setChecked(True)
        self.repeat = QSpinBox(); self.repeat.setRange(1, 1_000_000); self.repeat.setValue(1)
        self.gap_s = QDoubleSpinBox(); self.gap_s.setRange(0.0, 60.0); self.gap_s.setDecimals(3); self.gap_s.setSingleStep(0.1); self.gap_s.setValue(0.0)
        sched_form.addRow("", self.loop)
        sched_form.addRow("Repeat (N)", self.repeat)
        sched_form.addRow("Gap (s)", self.gap_s)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("Start TX")
        self.btn_stop = QPushButton("Stop")
        self.btn_load = QPushButton("Load Profile…")
        self.btn_save = QPushButton("Save as Profile…")

        # Initial button states (Stop disabled until TX starts)
        self.btn_stop.setEnabled(False)

        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_load)
        btn_row.addWidget(self.btn_save)

        # Assembling
        root.addWidget(dev_group)
        root.addWidget(rf_group)
        root.addWidget(mod_group)
        root.addWidget(pat_group)
        root.addWidget(sched_group)
        root.addLayout(btn_row)
        root.addStretch(1)

        # Wire buttons
        self.btn_load.clicked.connect(self._load_profile_dialog)
        self.btn_save.clicked.connect(self._save_profile_dialog)
        self.btn_start.clicked.connect(self._start_tx)
        self.btn_stop.clicked.connect(self._stop_tx)

        # Auto-load default profile if exists
        self._load_default_profile()

    # ---- helpers ----
    def _collect_profile(self):
        profile = {
            "name": None,
            "standard": "generic",
            "modulation": {
                "type": self.combo_mod.currentText(),
                "deviation_hz": int(self.deviation.value()),
                "pm_index": float(self.pm_index.value()),
                "am_depth": float(self.am_depth.value()),
            },
            "pattern": {
                "type": self.combo_pat.currentText(),
                "tone_hz": int(self.tone_hz.value()),
                "bitrate_bps": int(self.bitrate.value()),
            },
            "schedule": {
                "mode": "loop" if self.loop.isChecked() else "repeat",
                "gap_s": float(self.gap_s.value()),
                "repeat": int(self.repeat.value()),
            },
            "device": {
                "backend": self.combo_backend.currentText(),
                "fs_tx": int(self.fs_tx.value()),
                "tx_gain_db": int(self.tx_gain.value()),
                "pa": bool(self.pa_enable.isChecked()),
                "target_hz": int(self._safe_int(self.target_hz.text(), 0)),
                "if_offset_hz": int(self._safe_int(self.if_offset_hz.text(), 0)),
                "freq_corr_hz": int(self._safe_int(self.freq_corr_hz.text(), 0)),
            },
            "_meta": {
                "created_utc": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
            }
        }
        return profile

    def _save_profile_dialog(self):
        prof = self._collect_profile()

        # Open file save dialog in profiles directory
        pdir = str(profiles_dir())
        default_path = str(profiles_dir() / "profile_1.json")

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Profile",
            default_path,
            "Profiles (*.json)"
        )

        if not file_path:
            return  # User cancelled

        # Ensure .json extension
        if not file_path.endswith('.json'):
            file_path += '.json'

        out_path = Path(file_path)

        # Extract profile name from filename (without extension)
        prof["name"] = out_path.stem

        try:
            out_path.write_text(json.dumps(prof, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            QMessageBox.critical(self, "Save failed", f"Can't save profile:\n{e}")
            return
        self._status(f"Profile saved: {out_path.name}")

    def _load_default_profile(self):
        """Auto-load default.json profile if it exists on startup."""
        default_path = profiles_dir() / "default.json"
        if default_path.exists():
            try:
                data = json.loads(default_path.read_text(encoding="utf-8"))
                ok, msg = self._validate_profile(data)
                if ok:
                    self._apply_profile_to_form(data)
                    # Silently load - no status message on startup
            except Exception:
                pass  # Silently ignore errors in default profile

    def _load_profile_dialog(self):
        # Optional: migrate legacy profiles first
        try:
            from ...utils.migrate import migrate_legacy_profiles
            moved = migrate_legacy_profiles()
            if moved:
                self._status(f"Migrated {moved} legacy profiles to rfgen/profiles")
        except ImportError:
            pass  # migrate module doesn't exist yet, skip

        pdir = str(profiles_dir())
        path, _ = QFileDialog.getOpenFileName(self, "Load Profile", pdir, "Profiles (*.json)")
        if not path:
            return
        self._load_profile(Path(path))

    def _load_profile(self, path: Path):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            QMessageBox.critical(self, "Load failed", f"Can't read profile:\n{e}")
            return
        ok, msg = self._validate_profile(data)
        if not ok:
            QMessageBox.critical(self, "Invalid profile", msg)
            return
        self._apply_profile_to_form(data)
        self._status(f"Profile loaded: {path.name}")

    def _validate_profile(self, p: dict):
        """Validate profile structure and values."""
        # Check required top-level keys
        for key in ("device", "modulation", "pattern", "schedule"):
            if key not in p:
                return False, f"Missing top-level '{key}'"

        # Validate device.backend
        if p["device"].get("backend") not in ("hackrf", "fileout"):
            return False, "device.backend must be 'hackrf' or 'fileout'"

        # Validate modulation.type
        if p["modulation"].get("type") not in ("None", "AM", "FM", "PM"):
            return False, "modulation.type must be None/AM/FM/PM"

        # Validate numeric fields
        try:
            fs = int(p["device"].get("fs_tx", 0))
            if fs <= 0:
                return False, "device.fs_tx must be >0"
        except (ValueError, TypeError):
            return False, "device.fs_tx must be int"

        try:
            tx_gain = int(p["device"].get("tx_gain_db", 30))
            if tx_gain < 0 or tx_gain > 60:
                return False, "device.tx_gain_db must be in range 0-60"
        except (ValueError, TypeError):
            return False, "device.tx_gain_db must be int"

        # Validate modulation parameters
        try:
            dev = int(p["modulation"].get("deviation_hz", 5000))
            if dev < 0:
                return False, "modulation.deviation_hz must be >=0"
        except (ValueError, TypeError):
            return False, "modulation.deviation_hz must be int"

        try:
            pm_idx = float(p["modulation"].get("pm_index", 1.0))
            if pm_idx < 0 or pm_idx > 10:
                return False, "modulation.pm_index must be in range 0-10"
        except (ValueError, TypeError):
            return False, "modulation.pm_index must be float"

        try:
            am_depth = float(p["modulation"].get("am_depth", 0.5))
            if am_depth < 0 or am_depth > 1:
                return False, "modulation.am_depth must be in range 0-1"
        except (ValueError, TypeError):
            return False, "modulation.am_depth must be float"

        # Validate pattern fields
        try:
            tone = int(p["pattern"].get("tone_hz", 1000))
            if tone < 1:
                return False, "pattern.tone_hz must be >0"
        except (ValueError, TypeError):
            return False, "pattern.tone_hz must be int"

        try:
            bitrate = int(p["pattern"].get("bitrate_bps", 9600))
            if bitrate < 10:
                return False, "pattern.bitrate_bps must be >=10"
        except (ValueError, TypeError):
            return False, "pattern.bitrate_bps must be int"

        # Validate schedule fields
        try:
            repeat = int(p["schedule"].get("repeat", 1))
            if repeat < 1:
                return False, "schedule.repeat must be >=1"
        except (ValueError, TypeError):
            return False, "schedule.repeat must be int"

        try:
            gap = float(p["schedule"].get("gap_s", 0.0))
            if gap < 0:
                return False, "schedule.gap_s must be >=0"
        except (ValueError, TypeError):
            return False, "schedule.gap_s must be float"

        return True, ""

    def _apply_profile_to_form(self, p):
        """Map profile values to UI widgets."""
        # Device
        backend = str(p["device"].get("backend", "hackrf"))
        idx = self.combo_backend.findText(backend)
        if idx >= 0:
            self.combo_backend.setCurrentIndex(idx)

        self.fs_tx.setValue(int(p["device"].get("fs_tx", 2_000_000)))
        self.tx_gain.setValue(int(p["device"].get("tx_gain_db", 30)))
        self.pa_enable.setChecked(bool(p["device"].get("pa", False)))
        self.target_hz.setText(str(int(p["device"].get("target_hz", 0))))
        self.if_offset_hz.setText(str(int(p["device"].get("if_offset_hz", 0))))
        self.freq_corr_hz.setText(str(int(p["device"].get("freq_corr_hz", 0))))

        # Modulation
        mod_type = str(p["modulation"].get("type", "None"))
        idx = self.combo_mod.findText(mod_type)
        if idx >= 0:
            self.combo_mod.setCurrentIndex(idx)

        self.deviation.setValue(int(p["modulation"].get("deviation_hz", 5000)))
        self.pm_index.setValue(float(p["modulation"].get("pm_index", 1.0)))
        self.am_depth.setValue(float(p["modulation"].get("am_depth", 0.5)))

        # Pattern
        pat_type = str(p["pattern"].get("type", "Tone"))
        idx = self.combo_pat.findText(pat_type)
        if idx >= 0:
            self.combo_pat.setCurrentIndex(idx)

        self.tone_hz.setValue(int(p["pattern"].get("tone_hz", 1000)))
        self.bitrate.setValue(int(p["pattern"].get("bitrate_bps", 9600)))

        # Schedule
        mode = str(p["schedule"].get("mode", "loop")).lower()
        self.loop.setChecked(mode == "loop")
        self.repeat.setValue(int(p["schedule"].get("repeat", 1)))
        self.gap_s.setValue(float(p["schedule"].get("gap_s", 0.0)))

    def _start_tx(self):
        prof = self._collect_profile()
        backend = prof["device"]["backend"]
        fs = int(prof["device"]["fs_tx"])
        target = int(prof["device"]["target_hz"])
        if_hz = int(prof["device"]["if_offset_hz"])
        # if IF!=0: generate complex tone at +IF and set LO=center=target-IF
        center = target if if_hz == 0 else (target - if_hz)
        tx_gain = int(prof["device"]["tx_gain_db"])

        # Build IQ
        if self.combo_mod.currentText().lower() == "none":
            iq = build_cw(prof, frame_s=1.0)
        else:
            iq = build_iq(prof, frame_s=1.0)

        fob = FileOutBackend(out_dir())
        iq_path = Path(fob.write_sc8("quick_tx_frame", iq))  # <-- SC8

        if backend == "hackrf":
            self._hrf = HackRFTx()
            try:
                self._hrf.run_loop(iq_path, fs_tx=fs, center_hz=center, tx_gain_db=tx_gain)
            except Exception as e:
                QMessageBox.critical(self, "HackRF start failed",
                                     f"Failed to start hackrf_transfer.\n{e}\n"
                                     "Make sure HackRF tools are installed and in PATH.")
                self._hrf = None
                return

            # Update button states - disable Start/Save, enable Stop
            self.btn_start.setEnabled(False)
            self.btn_save.setEnabled(False)
            self.btn_load.setEnabled(False)
            self.btn_stop.setEnabled(True)

            # Show log path in status
            log = getattr(self._hrf, "log_path", None)
            if log:
                self._status(f"HackRF TX running (PID {self._hrf.pid}). Log: {log.name}")
            else:
                self._status(f"HackRF TX running (PID {self._hrf.pid}).")
        else:
            QMessageBox.information(self, "IQ generated",
                                    f"Generated 1s IQ to: {iq_path}\nBackend: fileout.")
            self._status("TX: generated 1s frame (fileout).")

    def _stop_tx(self):
        print("[DEBUG] _stop_tx called")  # DEBUG

        if self._hrf and self._hrf.is_running():
            print(f"[DEBUG] Process is running, PID: {self._hrf.pid}")  # DEBUG
            self._hrf.stop()
            print("[DEBUG] stop() returned")  # DEBUG
            self._status("HackRF TX stopped.")
        else:
            print("[DEBUG] No process to stop")  # DEBUG
            self._status("Nothing to stop.")

        # Always re-enable buttons after stop
        print("[DEBUG] Re-enabling buttons")  # DEBUG
        self.btn_start.setEnabled(True)
        self.btn_save.setEnabled(True)
        self.btn_load.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._hrf = None
        print("[DEBUG] _stop_tx finished")  # DEBUG

    def _status(self, msg: str):
        mw = self.window()
        if hasattr(mw, 'statusBar') and mw.statusBar():
            mw.statusBar().showMessage(msg, 5000)

    @staticmethod
    def _safe_int(text: str, default: int = 0) -> int:
        try:
            return int(str(text).strip())
        except Exception:
            return default
