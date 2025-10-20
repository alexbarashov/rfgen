"""DSC HF (Digital Selective Calling) signal generator page."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout, QPushButton,
    QComboBox, QLineEdit, QSpinBox, QGroupBox, QLabel, QCheckBox,
    QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt
from pathlib import Path
import datetime

from ...utils.paths import profiles_dir
from ...utils.profile_io import validate_profile, apply_defaults, load_json, save_json


class PageDSC_HF(QWidget):
    """DSC HF signal generator page.

    Features:
    - HF DSC frequencies (2, 4, 6, 8, 12, 16 MHz)
    - FSK modulation (170 Hz shift, 100 Bd)
    - Distress, urgency, safety, routine calls
    - ITU-R M.541 compliance
    - Test mode with patterns
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)

        # Header
        header = QLabel("<b>DSC HF Signal Generator</b>")
        header.setStyleSheet("font-size: 14pt;")
        root.addWidget(header)

        # Device group
        dev_group = QGroupBox("Device")
        dev_form = QFormLayout(dev_group)
        self.combo_backend = QComboBox()
        self.combo_backend.addItems(["hackrf", "fileout"])
        self.fs_tx = QSpinBox()
        self.fs_tx.setRange(200_000, 20_000_000)
        self.fs_tx.setSingleStep(100_000)
        self.fs_tx.setValue(2_000_000)
        self.tx_gain_device = QSpinBox()
        self.tx_gain_device.setRange(0, 60)
        self.tx_gain_device.setValue(30)
        self.pa_enable = QCheckBox("Enable PA")
        dev_form.addRow("Backend", self.combo_backend)
        dev_form.addRow("Fs TX (S/s)", self.fs_tx)
        dev_form.addRow("TX Gain (dB)", self.tx_gain_device)
        dev_form.addRow("", self.pa_enable)
        root.addWidget(dev_group)

        # Radio group
        rf_group = QGroupBox("Radio")
        rf_form = QFormLayout(rf_group)
        self.target_hz_radio = QLineEdit("2187500")  # Default: 2187.5 kHz
        self.if_offset_hz = QLineEdit("0")
        self.freq_corr_hz = QLineEdit("0")
        rf_form.addRow("Target (Hz)", self.target_hz_radio)
        rf_form.addRow("IF offset (Hz)", self.if_offset_hz)
        rf_form.addRow("Freq corr (Hz)", self.freq_corr_hz)
        root.addWidget(rf_group)

        # Frequency selection
        freq_group = QGroupBox("Frequency Selection")
        freq_layout = QFormLayout()

        self.combo_freq = QComboBox()
        self.combo_freq.addItems([
            "2187.5 kHz (Distress)",
            "4207.5 kHz",
            "6312.0 kHz",
            "8414.5 kHz",
            "12577.0 kHz",
            "16804.5 kHz"
        ])
        freq_layout.addRow("Frequency:", self.combo_freq)

        self.combo_freq.currentTextChanged.connect(self._on_freq_changed)

        freq_group.setLayout(freq_layout)
        root.addWidget(freq_group)

        # Call configuration
        call_group = QGroupBox("Call Configuration")
        call_layout = QFormLayout()

        self.combo_category = QComboBox()
        self.combo_category.addItems(["Distress", "Urgency", "Safety", "Routine", "Test"])
        call_layout.addRow("Category:", self.combo_category)

        self.combo_type = QComboBox()
        self.combo_type.addItems([
            "All Ships",
            "Individual Station",
            "Group Call",
            "Area Call"
        ])
        call_layout.addRow("Call Type:", self.combo_type)

        self.mmsi = QLineEdit("123456789")
        call_layout.addRow("MMSI:", self.mmsi)

        call_group.setLayout(call_layout)
        root.addWidget(call_group)

        # TX settings
        tx_group = QGroupBox("Transmission Settings")
        tx_layout = QFormLayout()

        self.repeat_count = QSpinBox()
        self.repeat_count.setRange(1, 10)
        self.repeat_count.setValue(1)
        tx_layout.addRow("Repeat Count:", self.repeat_count)

        tx_group.setLayout(tx_layout)
        root.addWidget(tx_group)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("Start TX")
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setEnabled(False)
        self.btn_save = QPushButton("Save as Profile...")
        self.btn_load = QPushButton("Load Profile...")

        self.btn_start.clicked.connect(self._start_tx)
        self.btn_stop.clicked.connect(self._stop_tx)
        self.btn_save.clicked.connect(self._save_profile)
        self.btn_load.clicked.connect(self._load_profile)

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_load)
        root.addLayout(btn_layout)

        # Status
        self.status_label = QLabel("Ready")
        root.addWidget(self.status_label)

        root.addStretch()

        # Auto-load default profile if exists
        self._load_default_profile()

    def _load_default_profile(self):
        """Auto-load default.json profile if it exists on startup."""
        default_path = profiles_dir() / "default.json"
        if default_path.exists():
            data = load_json(default_path)
            if data:
                # Check if profile matches this page's standard
                if data.get("standard") != "dsc_hf":
                    return  # Wrong standard, skip loading
                ok, msg = validate_profile(data)
                if ok:
                    self._apply_profile_to_form(data)
                    # Silently load - no status message on startup

    def _on_freq_changed(self, text):
        """Update frequency based on selection."""
        freq_map = {
            "2187.5 kHz": "2187500",
            "4207.5 kHz": "4207500",
            "6312.0 kHz": "6312000",
            "8414.5 kHz": "8414500",
            "12577.0 kHz": "12577000",
            "16804.5 kHz": "16804500"
        }

        for key, value in freq_map.items():
            if key in text:
                self.target_hz_radio.setText(value)
                return

    def _start_tx(self):
        """Start DSC HF transmission (placeholder)."""
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_label.setText("DSC HF transmission started (placeholder)")

    def _stop_tx(self):
        """Stop transmission (placeholder)."""
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_label.setText("Stopped")

    def _collect_profile(self):
        """Collect current settings into profile dictionary."""
        profile = {
            "name": None,
            "standard": "dsc_hf",
            "standard_params": {
                "frequency": self.combo_freq.currentText(),
                "category": self.combo_category.currentText(),
                "call_type": self.combo_type.currentText(),
                "mmsi": self.mmsi.text(),
            },
            "modulation": {
                "type": "FSK",
            },
            "pattern": {
                "type": "DSC_HF",
            },
            "schedule": {
                "mode": "repeat",
                "gap_s": 0.0,
                "repeat": int(self.repeat_count.value()),
            },
            "device": {
                "backend": self.combo_backend.currentText(),
                "fs_tx": int(self.fs_tx.value()),
                "tx_gain_db": int(self.tx_gain_device.value()),
                "pa": bool(self.pa_enable.isChecked()),
                "target_hz": int(self._safe_int(self.target_hz_radio.text(), 2187500)),
                "if_offset_hz": int(self._safe_int(self.if_offset_hz.text(), 0)),
                "freq_corr_hz": int(self._safe_int(self.freq_corr_hz.text(), 0)),
            },
            "_meta": {
                "created_utc": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
            }
        }
        return profile

    def _save_profile(self):
        """Save current settings as profile."""
        prof = self._collect_profile()

        default_path = str(profiles_dir() / "profile.json")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Profile",
            default_path,
            "Profiles (*.json)"
        )

        if not file_path:
            return

        if not file_path.endswith('.json'):
            file_path += '.json'

        out_path = Path(file_path)
        prof["name"] = out_path.stem

        if not save_json(out_path, prof):
            QMessageBox.critical(self, "Save failed", "Can't save profile")
            return
        self.status_label.setText(f"Profile saved: {out_path.name}")

    def _load_profile(self):
        """Load profile from file."""
        pdir = str(profiles_dir())
        path, _ = QFileDialog.getOpenFileName(self, "Load Profile", pdir, "Profiles (*.json)")
        if not path:
            return

        data = load_json(Path(path))
        if not data:
            QMessageBox.critical(self, "Load failed", "Can't read profile")
            return

        ok, msg = validate_profile(data)
        if not ok:
            QMessageBox.critical(self, "Invalid profile", msg)
            return

        self._apply_profile_to_form(data)
        self.status_label.setText(f"Profile loaded: {Path(path).name}")

    def _apply_profile_to_form(self, p):
        """Map profile values to UI widgets."""
        # Device
        backend = str(p.get("device", {}).get("backend", "hackrf"))
        idx = self.combo_backend.findText(backend)
        if idx >= 0:
            self.combo_backend.setCurrentIndex(idx)

        self.fs_tx.setValue(int(p.get("device", {}).get("fs_tx", 2_000_000)))
        self.tx_gain_device.setValue(int(p.get("device", {}).get("tx_gain_db", 30)))
        self.pa_enable.setChecked(bool(p.get("device", {}).get("pa", False)))
        self.target_hz_radio.setText(str(int(p.get("device", {}).get("target_hz", 2187500))))
        self.if_offset_hz.setText(str(int(p.get("device", {}).get("if_offset_hz", 0))))
        self.freq_corr_hz.setText(str(int(p.get("device", {}).get("freq_corr_hz", 0))))

        # Standard params
        sp = p.get("standard_params", {})

        # Frequency
        frequency = str(sp.get("frequency", "2187.5 kHz (Distress)"))
        idx = self.combo_freq.findText(frequency)
        if idx >= 0:
            self.combo_freq.setCurrentIndex(idx)

        # Category
        category = str(sp.get("category", "Distress"))
        idx = self.combo_category.findText(category)
        if idx >= 0:
            self.combo_category.setCurrentIndex(idx)

        # Call type
        call_type = str(sp.get("call_type", "All Ships"))
        idx = self.combo_type.findText(call_type)
        if idx >= 0:
            self.combo_type.setCurrentIndex(idx)

        # MMSI
        self.mmsi.setText(str(sp.get("mmsi", "123456789")))

        # Schedule
        self.repeat_count.setValue(int(p.get("schedule", {}).get("repeat", 1)))

    @staticmethod
    def _safe_int(text: str, default: int = 0) -> int:
        try:
            return int(str(text).strip())
        except Exception:
            return default
