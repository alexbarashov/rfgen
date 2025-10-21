"""COSPAS-SARSAT 406 MHz beacon signal generator page."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout, QPushButton,
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QGroupBox, QLabel, QCheckBox,
    QMessageBox, QFileDialog, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, QTimer
from pathlib import Path
import datetime

from ...utils.paths import profiles_dir
from ...utils.profile_io import validate_profile, apply_defaults, load_json, save_json


class Page406(QWidget):
    """406 MHz COSPAS-SARSAT beacon signal generator page.

    Features:
    - BPSK modulation
    - Beacon ID / Hex message input
    - FEC and interleaving presets
    - Test mode with BPSK patterns
    - WARNING: Use only with shielded test setup (legal restrictions)
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)

        # Header with warning
        header = QLabel("<b>406 MHz COSPAS-SARSAT Beacon Generator</b>")
        header.setStyleSheet("font-size: 14pt;")
        root.addWidget(header)

        warning = QLabel("⚠️ <b>WARNING:</b> Only use with shielded/attenuated test setup. "
                        "Transmission of false distress signals is illegal.")
        warning.setStyleSheet("color: red; background: #fff3cd; padding: 8px; border-radius: 4px;")
        warning.setWordWrap(True)
        root.addWidget(warning)

        # Device group
        dev_group = QGroupBox("Device")
        dev_form = QFormLayout(dev_group)
        self.combo_backend = QComboBox()
        self.combo_backend.addItems(["fileout", "hackrf"])
        self.fs_tx = QSpinBox()
        self.fs_tx.setRange(200_000, 20_000_000)
        self.fs_tx.setSingleStep(100_000)
        self.fs_tx.setValue(2_000_000)
        self.tx_gain_device = QSpinBox()
        self.tx_gain_device.setRange(0, 60)
        self.tx_gain_device.setValue(10)  # Low default for safety
        self.pa_enable = QCheckBox("Enable PA")
        dev_form.addRow("Backend", self.combo_backend)
        dev_form.addRow("Fs TX (S/s)", self.fs_tx)
        dev_form.addRow("TX Gain (dB)", self.tx_gain_device)
        dev_form.addRow("", self.pa_enable)
        root.addWidget(dev_group)

        # Radio group
        rf_group = QGroupBox("Radio")
        rf_form = QFormLayout(rf_group)
        self.target_hz = QLineEdit("406040000")  # 406.040 MHz
        self.if_offset_hz = QLineEdit("0")
        self.freq_corr_hz = QLineEdit("0")
        rf_form.addRow("Target (Hz)", self.target_hz)
        rf_form.addRow("IF offset (Hz)", self.if_offset_hz)
        rf_form.addRow("Freq corr (Hz)", self.freq_corr_hz)
        root.addWidget(rf_group)

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
        self.combo_msg_type.addItems([
            "Standard Location (Hex ID)",
            "User Location (GPS)",
            "Test Message",
            "BPSK Pattern (Debug)"
        ])
        form_layout.addRow("Message Type:", self.combo_msg_type)

        self.beacon_id = QLineEdit("123456789ABCDEF")
        self.beacon_id.setPlaceholderText("15-bit hex beacon ID")
        form_layout.addRow("Beacon ID (Hex):", self.beacon_id)

        self.lat = QLineEdit("0.0")
        form_layout.addRow("Latitude:", self.lat)

        self.lon = QLineEdit("0.0")
        form_layout.addRow("Longitude:", self.lon)

        # Direct HEX field (enabled by default)
        self.hex_message = QLineEdit("FFFED080020000007FDFFB0020B783E0F66C")
        self.hex_message.setPlaceholderText("Raw hex message data")
        form_layout.addRow("HEX Message:", self.hex_message)

        msg_layout.addLayout(form_layout)
        msg_group.setLayout(msg_layout)
        root.addWidget(msg_group)

        # Connect mode switch (will be set after timer initialization)
        # Initial state will be set after timer creation

        # PSK-406 parameters
        psk_group = QGroupBox("PSK-406 Parameters")
        psk_layout = QFormLayout()

        self.phase_low = QDoubleSpinBox()
        self.phase_low.setRange(-3.14, 3.14)
        self.phase_low.setSingleStep(0.1)
        self.phase_low.setDecimals(2)
        self.phase_low.setValue(-1.1)
        self.phase_low.setSuffix(" rad")
        psk_layout.addRow("Phase Low:", self.phase_low)

        self.phase_high = QDoubleSpinBox()
        self.phase_high.setRange(-3.14, 3.14)
        self.phase_high.setSingleStep(0.1)
        self.phase_high.setDecimals(2)
        self.phase_high.setValue(1.1)
        self.phase_high.setSuffix(" rad")
        psk_layout.addRow("Phase High:", self.phase_high)

        self.front_samples = QSpinBox()
        self.front_samples.setRange(10, 500)
        self.front_samples.setValue(75)
        self.front_samples.setSuffix(" samples")
        psk_layout.addRow("Front Samples:", self.front_samples)

        psk_group.setLayout(psk_layout)
        root.addWidget(psk_group)

        # Encoding settings
        enc_group = QGroupBox("Encoding Settings")
        enc_layout = QFormLayout()

        self.combo_fec = QComboBox()
        self.combo_fec.addItems(["BCH (Long)", "BCH (Short)", "None (Test)"])
        enc_layout.addRow("FEC:", self.combo_fec)

        self.interleave = QCheckBox("Enable Interleaving")
        self.interleave.setChecked(True)
        enc_layout.addRow("", self.interleave)

        enc_group.setLayout(enc_layout)
        root.addWidget(enc_group)

        # TX settings
        tx_group = QGroupBox("Transmission Settings")
        tx_layout = QFormLayout()

        self.frame_count = QSpinBox()
        self.frame_count.setRange(1, 100)
        self.frame_count.setValue(1)
        tx_layout.addRow("Frame Count:", self.frame_count)

        tx_group.setLayout(tx_layout)
        root.addWidget(tx_group)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("Generate")
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
        self.status_label = QLabel("Ready - Select backend and configure message")
        root.addWidget(self.status_label)

        root.addStretch()

        # Auto-save timer (debounce)
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(1000)  # 1 second delay
        self._autosave_timer.timeout.connect(self._do_autosave)

        # Auto-load default profile if exists
        self._load_default_profile()

        # Connect value change signals to auto-save
        self._connect_autosave_signals()

        # Connect mode switch and set initial state (after timer is created)
        self.radio_hex.toggled.connect(self._on_mode_changed)
        self.radio_builder.toggled.connect(self._on_mode_changed)
        self._on_mode_changed()  # Set initial field states

    def _on_mode_changed(self):
        """Handle mode switching between Direct HEX and Message Builder."""
        is_hex_mode = self.radio_hex.isChecked()

        # Direct HEX mode: enable hex_message, disable builder fields
        # Message Builder mode: disable hex_message, enable builder fields
        self.hex_message.setEnabled(is_hex_mode)
        self.combo_msg_type.setEnabled(not is_hex_mode)
        self.beacon_id.setEnabled(not is_hex_mode)
        self.lat.setEnabled(not is_hex_mode)
        self.lon.setEnabled(not is_hex_mode)

        # Trigger autosave when mode changes
        self._autosave_to_default()

    def _load_default_profile(self):
        """Auto-load default.json profile if it exists on startup."""
        from ...utils.profile_io import defaults, apply_defaults

        default_path = profiles_dir() / "default.json"

        # If default.json exists and matches this page's standard, load it
        if default_path.exists():
            data = load_json(default_path)
            if data and data.get("standard") == "c406":
                ok, msg = validate_profile(data)
                if ok:
                    self._apply_profile_to_form(data)
                    return  # Successfully loaded

        # Otherwise, create default profile for c406 and apply it
        default_profile = defaults()
        default_profile["name"] = "default"
        default_profile["standard"] = "c406"
        default_profile["standard_params"] = {
            "input_mode": "hex",  # Default to Direct HEX mode
            "msg_type": "Standard Location (Hex ID)",
            "beacon_id": "123456789ABCDEF",
            "lat": "0.0",
            "lon": "0.0",
            "hex_message": "FFFED080020000007FDFFB0020B783E0F66C",
            "phase_low": -1.1,
            "phase_high": 1.1,
            "front_samples": 75,
            "fec": "BCH (Long)",
            "interleave": True,
            "frame_count": 1,
        }
        default_profile["modulation"] = {"type": "BPSK"}
        default_profile["pattern"] = {"type": "406"}
        default_profile["schedule"] = {"mode": "repeat", "gap_s": 0.0, "repeat": 1}
        # Use values from profile_io.defaults() but override for c406
        default_profile["device"]["backend"] = "hackrf"  # From general defaults
        default_profile["device"]["tx_gain_db"] = 30  # From general defaults
        default_profile["device"]["target_hz"] = 406040000  # 406.040 MHz

        # Apply default profile to form
        self._apply_profile_to_form(default_profile)

        # Save as default.json for next time
        save_json(default_path, default_profile)

    def _connect_autosave_signals(self):
        """Connect widget signals to auto-save default profile."""
        # Device параметры
        self.combo_backend.currentTextChanged.connect(self._autosave_to_default)
        self.fs_tx.valueChanged.connect(self._autosave_to_default)
        self.tx_gain_device.valueChanged.connect(self._autosave_to_default)
        self.pa_enable.stateChanged.connect(self._autosave_to_default)
        self.target_hz.textChanged.connect(self._autosave_to_default)
        self.if_offset_hz.textChanged.connect(self._autosave_to_default)
        self.freq_corr_hz.textChanged.connect(self._autosave_to_default)

        # Standard параметры
        self.combo_msg_type.currentTextChanged.connect(self._autosave_to_default)
        self.beacon_id.textChanged.connect(self._autosave_to_default)
        self.lat.textChanged.connect(self._autosave_to_default)
        self.lon.textChanged.connect(self._autosave_to_default)
        self.hex_message.textChanged.connect(self._autosave_to_default)
        self.phase_low.valueChanged.connect(self._autosave_to_default)
        self.phase_high.valueChanged.connect(self._autosave_to_default)
        self.front_samples.valueChanged.connect(self._autosave_to_default)
        self.combo_fec.currentTextChanged.connect(self._autosave_to_default)
        self.interleave.stateChanged.connect(self._autosave_to_default)
        self.frame_count.valueChanged.connect(self._autosave_to_default)

    def _autosave_to_default(self):
        """Trigger auto-save with debounce."""
        # Restart timer on every change
        self._autosave_timer.start()

    def _do_autosave(self):
        """Actually save current settings to default.json."""
        try:
            prof = self._collect_profile()
            prof["name"] = "default"
            default_path = profiles_dir() / "default.json"
            save_json(default_path, prof)
        except Exception:
            pass  # Silent fail for autosave

    def _collect_profile(self):
        """Collect current settings into profile dictionary."""
        profile = {
            "name": None,
            "standard": "c406",
            "standard_params": {
                "input_mode": "hex" if self.radio_hex.isChecked() else "builder",
                "msg_type": self.combo_msg_type.currentText(),
                "beacon_id": self.beacon_id.text(),
                "lat": self.lat.text(),
                "lon": self.lon.text(),
                "hex_message": self.hex_message.text(),
                "phase_low": float(self.phase_low.value()),
                "phase_high": float(self.phase_high.value()),
                "front_samples": int(self.front_samples.value()),
                "fec": self.combo_fec.currentText(),
                "interleave": self.interleave.isChecked(),
                "frame_count": int(self.frame_count.value()),
            },
            "modulation": {
                "type": "BPSK",
            },
            "pattern": {
                "type": "406",
            },
            "schedule": {
                "mode": "repeat",
                "gap_s": 0.0,
                "repeat": 1,
            },
            "device": {
                "backend": self.combo_backend.currentText(),
                "fs_tx": int(self.fs_tx.value()),
                "tx_gain_db": int(self.tx_gain_device.value()),
                "pa": bool(self.pa_enable.isChecked()),
                "target_hz": int(self._safe_int(self.target_hz.text(), 406040000)),
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
            self, "Save Profile", default_path, "Profiles (*.json)")

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
        # ВАЖНО: Отключаем автосохранение на время загрузки
        self._autosave_timer.stop()

        # Device
        backend = str(p.get("device", {}).get("backend", "fileout"))
        idx = self.combo_backend.findText(backend)
        if idx >= 0:
            self.combo_backend.setCurrentIndex(idx)

        self.fs_tx.setValue(int(p.get("device", {}).get("fs_tx", 2_000_000)))
        self.tx_gain_device.setValue(int(p.get("device", {}).get("tx_gain_db", 10)))
        self.pa_enable.setChecked(bool(p.get("device", {}).get("pa", False)))
        self.target_hz.setText(str(int(p.get("device", {}).get("target_hz", 406040000))))
        self.if_offset_hz.setText(str(int(p.get("device", {}).get("if_offset_hz", 0))))
        self.freq_corr_hz.setText(str(int(p.get("device", {}).get("freq_corr_hz", 0))))

        # Standard params
        sp = p.get("standard_params", {})

        # Input mode (hex or builder)
        input_mode = str(sp.get("input_mode", "hex"))
        if input_mode == "hex":
            self.radio_hex.setChecked(True)
        else:
            self.radio_builder.setChecked(True)
        # Mode change will be handled by _on_mode_changed() signal

        # Message type
        msg_type = str(sp.get("msg_type", "Standard Location (Hex ID)"))
        idx = self.combo_msg_type.findText(msg_type)
        if idx >= 0:
            self.combo_msg_type.setCurrentIndex(idx)

        self.beacon_id.setText(str(sp.get("beacon_id", "123456789ABCDEF")))
        self.lat.setText(str(sp.get("lat", "0.0")))
        self.lon.setText(str(sp.get("lon", "0.0")))
        self.hex_message.setText(str(sp.get("hex_message", "FFFED080020000007FDFFB0020B783E0F66C")))

        # PSK parameters
        self.phase_low.setValue(float(sp.get("phase_low", -1.1)))
        self.phase_high.setValue(float(sp.get("phase_high", 1.1)))
        self.front_samples.setValue(int(sp.get("front_samples", 75)))

        # FEC
        fec = str(sp.get("fec", "BCH (Long)"))
        idx = self.combo_fec.findText(fec)
        if idx >= 0:
            self.combo_fec.setCurrentIndex(idx)

        self.interleave.setChecked(bool(sp.get("interleave", True)))
        self.frame_count.setValue(int(sp.get("frame_count", 1)))

        # После загрузки всех значений - триггерим автосохранение
        # чтобы сохранить загруженный профиль в default.json
        self._autosave_to_default()

    def _start_tx(self):
        """Start 406 MHz transmission."""
        # Collect profile
        try:
            prof = self._collect_profile()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to collect profile: {e}")
            return

        backend = prof["device"]["backend"]

        if backend == "fileout":
            self._start_fileout(prof)
        elif backend == "hackrf":
            self._start_hackrf(prof)
        else:
            QMessageBox.warning(self, "Error", f"Unknown backend: {backend}")

    def _start_fileout(self, prof):
        """Generate and save to file."""
        from ...standards.psk406 import generate_psk406
        from ...utils.paths import profiles_dir
        import numpy as np

        try:
            # Generate IQ
            self.status_label.setText("Generating PSK-406 signal...")
            self.update()

            iq = generate_psk406(prof)

            # Save to file
            from PySide6.QtWidgets import QFileDialog
            default_path = str(profiles_dir() / "psk406_output.cf32")
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save IQ File", default_path, "cf32 Files (*.cf32);;All Files (*.*)")

            if not file_path:
                self.status_label.setText("Cancelled")
                return

            # Write interleaved float32 I,Q
            inter = np.empty(iq.size * 2, dtype=np.float32)
            inter[0::2] = iq.real.astype(np.float32, copy=False)
            inter[1::2] = iq.imag.astype(np.float32, copy=False)
            with open(file_path, "wb") as f:
                inter.tofile(f)

            self.status_label.setText(f"Saved: {Path(file_path).name}")
            QMessageBox.information(self, "Success", f"IQ file saved to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Generation Failed", str(e))
            self.status_label.setText(f"Error: {e}")

    def _start_hackrf(self, prof):
        """Generate and transmit via HackRF."""
        from ...standards.psk406 import generate_psk406
        from ...backends.hackrf import HackRFTx
        from ...utils.paths import profiles_dir
        import numpy as np

        try:
            # Generate IQ
            self.status_label.setText("Generating PSK-406 signal...")
            self.update()

            iq = generate_psk406(prof)

            # Save to temp file
            temp_path = profiles_dir() / "temp_psk406.cf32"
            inter = np.empty(iq.size * 2, dtype=np.float32)
            inter[0::2] = iq.real.astype(np.float32, copy=False)
            inter[1::2] = iq.imag.astype(np.float32, copy=False)
            with open(temp_path, "wb") as f:
                inter.tofile(f)

            # Calculate center frequency
            target_hz = prof["device"]["target_hz"]
            if_offset_hz = prof["device"]["if_offset_hz"]
            freq_corr_hz = prof["device"]["freq_corr_hz"]
            center_hz = target_hz + if_offset_hz + freq_corr_hz

            # Start HackRF
            self.status_label.setText("Starting HackRF transmission...")
            self.update()

            hackrf = HackRFTx()
            hackrf.run_loop(
                iq_path=temp_path,
                fs_tx=prof["device"]["fs_tx"],
                center_hz=int(center_hz),
                tx_gain_db=prof["device"]["tx_gain_db"]
            )

            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.status_label.setText(f"Transmitting on {target_hz/1e6:.3f} MHz (loop mode)")

            # Store hackrf instance for stopping
            self._hackrf = hackrf

        except Exception as e:
            QMessageBox.critical(self, "TX Failed", str(e))
            self.status_label.setText(f"Error: {e}")

    def _stop_tx(self):
        """Stop transmission."""
        if hasattr(self, '_hackrf'):
            try:
                self._hackrf.stop()
                self.status_label.setText("Stopped")
            except Exception as e:
                self.status_label.setText(f"Stop error: {e}")
            finally:
                delattr(self, '_hackrf')

        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    @staticmethod
    def _safe_int(text: str, default: int = 0) -> int:
        try:
            return int(str(text).strip())
        except Exception:
            return default
