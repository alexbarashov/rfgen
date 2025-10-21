"""AIS (Automatic Identification System) signal generator page."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout, QPushButton,
    QComboBox, QLineEdit, QSpinBox, QGroupBox, QLabel, QTextEdit, QCheckBox,
    QMessageBox, QFileDialog, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt
from pathlib import Path
import datetime

from ...utils.paths import profiles_dir
from ...utils.profile_io import validate_profile, apply_defaults, load_json, save_json


class PageAIS(QWidget):
    """AIS signal generator page.

    Features:
    - GMSK modulation (9600 bps, BT≈0.4)
    - Channel A/B selection or manual frequency
    - NMEA VDM message import
    - Test mode with PRBS/patterns
    - Continuous transmission mode
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)

        # Header
        header = QLabel("<b>AIS Signal Generator</b>")
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
        self.target_hz_radio = QLineEdit("162025000")
        self.if_offset_hz = QLineEdit("0")
        self.freq_corr_hz = QLineEdit("0")
        rf_form.addRow("Target (Hz)", self.target_hz_radio)
        rf_form.addRow("IF offset (Hz)", self.if_offset_hz)
        rf_form.addRow("Freq corr (Hz)", self.freq_corr_hz)
        root.addWidget(rf_group)

        # Channel selection
        channel_group = QGroupBox("Channel Configuration")
        channel_layout = QFormLayout()

        self.combo_channel = QComboBox()
        self.combo_channel.addItems(["Channel A (161.975 MHz)", "Channel B (162.025 MHz)", "Custom"])
        channel_layout.addRow("Channel:", self.combo_channel)

        self.combo_channel.currentTextChanged.connect(self._on_channel_changed)

        channel_group.setLayout(channel_layout)
        root.addWidget(channel_group)

        # Message configuration
        msg_group = QGroupBox("Message Configuration")
        msg_layout = QVBoxLayout()

        # Mode selection (Radio buttons)
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Input Mode:")
        self.radio_hex = QRadioButton("Direct HEX")
        self.radio_builder = QRadioButton("Message Builder")
        self.radio_hex.setChecked(True)  # Default: Direct HEX

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.radio_hex, 0)
        self.mode_group.addButton(self.radio_builder, 1)

        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.radio_hex)
        mode_layout.addWidget(self.radio_builder)
        mode_layout.addStretch()
        msg_layout.addLayout(mode_layout)

        # Form fields
        form_layout = QFormLayout()

        # Message Builder fields (disabled by default)
        self.combo_msg_type = QComboBox()
        self.combo_msg_type.addItems(["Position Report (1/2/3)", "Base Station (4)", "Static Data (5)", "Test Pattern"])
        form_layout.addRow("Message Type:", self.combo_msg_type)

        self.mmsi = QLineEdit("123456789")
        form_layout.addRow("MMSI:", self.mmsi)

        self.payload_input = QTextEdit()
        self.payload_input.setMaximumHeight(80)
        self.payload_input.setPlaceholderText("Payload (hex or NMEA VDM format)")
        form_layout.addRow("Payload:", self.payload_input)

        # Direct HEX field (enabled by default)
        self.hex_message = QLineEdit("")
        self.hex_message.setPlaceholderText("Raw AIS hex payload (e.g., 15MwkT0P...)")
        form_layout.addRow("HEX Message:", self.hex_message)

        msg_layout.addLayout(form_layout)

        msg_group.setLayout(msg_layout)
        root.addWidget(msg_group)

        # Connect mode change signal
        self.radio_hex.toggled.connect(self._on_mode_changed)
        self.radio_builder.toggled.connect(self._on_mode_changed)
        self._on_mode_changed()  # Set initial field states

        # TX settings
        tx_group = QGroupBox("Transmission Settings")
        tx_layout = QFormLayout()

        self.repeat_count = QSpinBox()
        self.repeat_count.setRange(1, 1000)
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
                if data.get("standard") != "ais":
                    return  # Wrong standard, skip loading
                ok, msg = validate_profile(data)
                if ok:
                    self._apply_profile_to_form(data)
                    # Silently load - no status message on startup

    def _on_channel_changed(self, text):
        """Update frequency based on channel selection."""
        if "Channel A" in text:
            self.target_hz_radio.setText("161975000")
        elif "Channel B" in text:
            self.target_hz_radio.setText("162025000")

    def _on_mode_changed(self):
        """Handle mode switching between Direct HEX and Message Builder."""
        is_hex_mode = self.radio_hex.isChecked()

        # Direct HEX mode: enable hex_message, disable builder fields
        # Message Builder mode: disable hex_message, enable builder fields
        self.hex_message.setEnabled(is_hex_mode)
        self.combo_msg_type.setEnabled(not is_hex_mode)
        self.mmsi.setEnabled(not is_hex_mode)
        self.payload_input.setEnabled(not is_hex_mode)

    def _collect_profile(self):
        """Collect current settings into profile dictionary."""
        profile = {
            "name": None,
            "standard": "ais",
            "standard_params": {
                "input_mode": "hex" if self.radio_hex.isChecked() else "builder",
                "channel": self.combo_channel.currentText(),
                "msg_type": self.combo_msg_type.currentText(),
                "mmsi": self.mmsi.text(),
                "payload": self.payload_input.toPlainText(),
                "hex_message": self.hex_message.text(),
            },
            "modulation": {
                "type": "GMSK",
            },
            "pattern": {
                "type": "AIS",
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
                "target_hz": int(self._safe_int(self.target_hz_radio.text(), 162025000)),
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
        self.target_hz_radio.setText(str(int(p.get("device", {}).get("target_hz", 162025000))))
        self.if_offset_hz.setText(str(int(p.get("device", {}).get("if_offset_hz", 0))))
        self.freq_corr_hz.setText(str(int(p.get("device", {}).get("freq_corr_hz", 0))))

        # Standard params
        sp = p.get("standard_params", {})

        # Channel
        channel = str(sp.get("channel", "Channel B (162.025 MHz)"))
        idx = self.combo_channel.findText(channel)
        if idx >= 0:
            self.combo_channel.setCurrentIndex(idx)

        # Message type
        msg_type = str(sp.get("msg_type", "Position Report (1/2/3)"))
        idx = self.combo_msg_type.findText(msg_type)
        if idx >= 0:
            self.combo_msg_type.setCurrentIndex(idx)

        self.mmsi.setText(str(sp.get("mmsi", "123456789")))
        self.payload_input.setPlainText(str(sp.get("payload", "")))
        self.hex_message.setText(str(sp.get("hex_message", "")))

        # Input mode (hex or builder)
        input_mode = str(sp.get("input_mode", "hex"))
        if input_mode == "hex":
            self.radio_hex.setChecked(True)
        else:
            self.radio_builder.setChecked(True)
        # Mode change will be handled by _on_mode_changed() signal

        # Schedule
        self.repeat_count.setValue(int(p.get("schedule", {}).get("repeat", 1)))

    def _start_tx(self):
        """Start AIS transmission (placeholder)."""
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_label.setText("AIS transmission started (placeholder)")

    def _stop_tx(self):
        """Stop AIS transmission (placeholder)."""
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_label.setText("AIS transmission stopped")

    @staticmethod
    def _safe_int(text: str, default: int = 0) -> int:
        try:
            return int(str(text).strip())
        except Exception:
            return default
