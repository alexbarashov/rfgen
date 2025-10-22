"""AIS (Automatic Identification System) signal generator page."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout, QPushButton,
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QGroupBox, QLabel, QTextEdit, QCheckBox,
    QMessageBox, QFileDialog, QRadioButton, QButtonGroup, QScrollArea
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

        # Главный layout для всей страницы
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        # Контейнер для содержимого
        content = QWidget()
        root = QVBoxLayout(content)
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
        self.hex_message = QLineEdit("24e98f59effffff33c8d603412140e10f002010384ab70")
        self.hex_message.setPlaceholderText("Raw AIS hex payload")
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
        tx_layout = QVBoxLayout()

        # Mode selection (Loop vs Finite)
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Mode:")
        self.radio_loop = QRadioButton("Loop (endless)")
        self.radio_finite = QRadioButton("Finite (N frames)")
        self.radio_loop.setChecked(True)  # Default: Loop

        self.tx_mode_group = QButtonGroup(self)
        self.tx_mode_group.addButton(self.radio_loop, 0)
        self.tx_mode_group.addButton(self.radio_finite, 1)

        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.radio_loop)
        mode_layout.addWidget(self.radio_finite)
        mode_layout.addStretch()
        tx_layout.addLayout(mode_layout)

        # Form fields
        tx_form = QFormLayout()

        # Frame count (only for Finite mode)
        self.frame_count = QSpinBox()
        self.frame_count.setRange(1, 10000)
        self.frame_count.setValue(5)
        tx_form.addRow("Frame Count:", self.frame_count)

        # Gap between frames
        self.gap_s = QDoubleSpinBox()
        self.gap_s.setRange(0.0, 60.0)
        self.gap_s.setSingleStep(0.1)
        self.gap_s.setDecimals(1)
        self.gap_s.setValue(8.0)
        self.gap_s.setSuffix(" s")
        tx_form.addRow("Gap between frames:", self.gap_s)

        tx_layout.addLayout(tx_form)
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

        # Установка контейнера в scroll area
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        # Backend instance
        self._hackrf_backend = None

        # Auto-load default profile if exists
        self._load_default_profile()

        # Connect TX mode switch
        self.radio_loop.toggled.connect(self._on_tx_mode_changed)
        self.radio_finite.toggled.connect(self._on_tx_mode_changed)
        self._on_tx_mode_changed()  # Set initial TX field states

    def _on_tx_mode_changed(self):
        """Handle TX mode switching between Loop and Finite."""
        is_finite = self.radio_finite.isChecked()
        # Frame count only enabled in Finite mode
        self.frame_count.setEnabled(is_finite)

    def _load_default_profile(self):
        """Auto-load default_ais.json profile if it exists on startup."""
        default_path = profiles_dir() / "default_ais.json"
        if default_path.exists():
            data = load_json(default_path)
            if data:
                # Verify it's the correct standard (safety check)
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
                "mode": "loop" if self.radio_loop.isChecked() else "repeat",
                "gap_s": float(self.gap_s.value()),
                "repeat": int(self.frame_count.value()),
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
        schedule = p.get("schedule", {})
        mode = str(schedule.get("mode", "loop"))
        if mode == "loop":
            self.radio_loop.setChecked(True)
        else:
            self.radio_finite.setChecked(True)
        # TX mode change will be handled by _on_tx_mode_changed() signal

        self.frame_count.setValue(int(schedule.get("repeat", 5)))
        self.gap_s.setValue(float(schedule.get("gap_s", 8.0)))

    def _start_tx(self):
        """Start AIS transmission."""
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
        """Generate and save AIS to file."""
        from ...core.wave_engine import build_ais
        from ...utils.paths import profiles_dir
        from ...utils.cf32_naming import generate_cf32_name
        import numpy as np

        try:
            # Generate IQ
            self.status_label.setText("Generating AIS signal...")
            self.update()

            iq = build_ais(prof)

            # Generate default filename with Fs (convention: iq_<FSk>_ais.cf32)
            fs_tx = prof["device"]["fs_tx"]
            default_filename = generate_cf32_name(fs_tx, "ais")
            default_path = str(profiles_dir() / default_filename)

            # Save to file
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
        """Generate and transmit AIS via HackRF."""
        from ...core.wave_engine import build_ais
        from ...backends.hackrf import HackRFTx
        from ...utils.paths import out_dir, logs_dir
        from ...utils.cf32_naming import generate_cf32_name
        from ...core.resample import resample_iq
        import numpy as np

        try:
            # Generate IQ
            self.status_label.setText("Generating AIS signal...")
            self.update()

            # 1. Generate baseband IQ
            iq_baseband = build_ais(prof)

            # 2. Resample if needed (from baseband to TX sample rate)
            fs_tx = prof["device"]["fs_tx"]
            fs_baseband = fs_tx  # AIS generates directly at TX rate

            # If we want to support different baseband rates in future:
            # fs_baseband = prof.get("device", {}).get("fs_baseband", fs_tx)
            # if fs_baseband != fs_tx:
            #     iq_tx = resample_iq(iq_baseband, fs_baseband, fs_tx)
            # else:
            #     iq_tx = iq_baseband
            iq_tx = iq_baseband

            # 3. Apply IF shift and freq correction (handled by HackRF backend)
            # Backend will apply digital shift automatically

            # 4. Handle schedule mode
            schedule = prof.get("schedule", {})
            mode = schedule.get("mode", "loop")
            gap_s = float(schedule.get("gap_s", 8.0))
            repeat_count = int(schedule.get("repeat", 5))

            if mode == "repeat":
                # Create gap (zeros)
                gap_samples = int(fs_tx * gap_s)
                gap = np.zeros(gap_samples, dtype=np.complex64)

                # Concatenate frame + gap, repeated N times
                iq_tx = np.tile(np.concatenate([iq_tx, gap]), repeat_count)
            elif mode == "loop":
                # Add gap inside the frame for loop mode
                gap_samples = int(fs_tx * gap_s)
                gap = np.zeros(gap_samples, dtype=np.complex64)
                iq_tx = np.concatenate([iq_tx, gap])
                # repeat_count will be handled by -R flag (infinite loop)
                repeat_count = 0  # 0 = infinite loop

            # 5. Save to temporary file
            temp_filename = generate_cf32_name(fs_tx, "temp_ais", add_timestamp=False)
            temp_path = out_dir() / temp_filename

            # Write interleaved float32 I,Q
            inter = np.empty(iq_tx.size * 2, dtype=np.float32)
            inter[0::2] = iq_tx.real.astype(np.float32, copy=False)
            inter[1::2] = iq_tx.imag.astype(np.float32, copy=False)
            with open(temp_path, "wb") as f:
                inter.tofile(f)

            # 6. Start HackRF
            self.status_label.setText("Starting HackRF transmission...")
            self.update()

            # Calculate center frequency (invariant: RF = target)
            target_hz = prof["device"]["target_hz"]
            if_offset_hz = prof["device"]["if_offset_hz"]
            freq_corr_hz = prof["device"]["freq_corr_hz"]
            center_hz = target_hz + if_offset_hz + freq_corr_hz

            tx_gain_db = prof["device"]["tx_gain_db"]
            pa_enable = prof["device"]["pa"]

            # Create HackRF backend
            self._hackrf_backend = HackRFTx()

            # Run transmission
            if mode == "loop":
                # Loop mode: use -R flag for infinite repeat
                self._hackrf_backend.run_loop(
                    str(temp_path),
                    fs_tx,
                    center_hz,
                    tx_gain_db,
                    pa_enable=pa_enable,
                    if_offset_hz=if_offset_hz,
                    freq_corr_hz=freq_corr_hz
                )
            else:
                # Repeat mode: file already contains N repetitions
                self._hackrf_backend.run_loop(
                    str(temp_path),
                    fs_tx,
                    center_hz,
                    tx_gain_db,
                    pa_enable=pa_enable,
                    if_offset_hz=if_offset_hz,
                    freq_corr_hz=freq_corr_hz
                )

            # Update UI
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.btn_save.setEnabled(False)
            self.btn_load.setEnabled(False)

            self.status_label.setText(
                f"TX: {target_hz/1e6:.3f} MHz, Fs={fs_tx/1e6:.1f} MS/s, "
                f"Gain={tx_gain_db} dB {'PA' if pa_enable else ''}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Transmission Failed", str(e))
            self.status_label.setText(f"Error: {e}")

    def _stop_tx(self):
        """Stop AIS transmission."""
        if hasattr(self, '_hackrf_backend') and self._hackrf_backend:
            try:
                self.status_label.setText("Stopping HackRF...")
                self.update()

                self._hackrf_backend.stop()

                self.status_label.setText("Stopped")
            except Exception as e:
                self.status_label.setText(f"Stop error: {e}")
            finally:
                self._hackrf_backend = None

        # Restore buttons
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_save.setEnabled(True)
        self.btn_load.setEnabled(True)

    @staticmethod
    def _safe_int(text: str, default: int = 0) -> int:
        try:
            return int(str(text).strip())
        except Exception:
            return default
