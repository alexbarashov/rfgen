from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout, QPushButton,
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox,
    QInputDialog, QMessageBox
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
        self.btn_save = QPushButton("Save as Profile…")
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)
        btn_row.addStretch(1)
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
        self.btn_save.clicked.connect(self._save_profile_dialog)
        self.btn_start.clicked.connect(self._start_tx)
        self.btn_stop.clicked.connect(self._stop_tx)

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
        name, ok = QInputDialog.getText(self, "Save Profile", "Profile name:", text="profile_1")
        if not ok or not name.strip():
            return
        prof["name"] = name.strip()

        out_path = profiles_dir() / f"{prof['name']}.json"
        try:
            out_path.write_text(json.dumps(prof, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            QMessageBox.critical(self, "Save failed", f"Can't save profile:\n{e}")
            return
        self._status(f"Profile saved: {out_path}")

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
                return
            self._status(f"HackRF TX running (center={center} Hz, fs={fs}). Looping {iq_path.name}")
        else:
            QMessageBox.information(self, "IQ generated",
                                    f"Generated 1s IQ to: {iq_path}\nBackend: fileout.")
            self._status("TX: generated 1s frame (fileout).")

    def _stop_tx(self):
        if self._hrf and self._hrf.is_running():
            self._hrf.stop()
            self._status("HackRF TX stopped.")
            self._hrf = None
        else:
            self._status("Nothing to stop.")

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
