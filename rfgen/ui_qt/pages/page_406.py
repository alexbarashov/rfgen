"""COSPAS-SARSAT 406 MHz beacon signal generator page."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout, QPushButton,
    QComboBox, QLineEdit, QSpinBox, QGroupBox, QLabel, QCheckBox
)
from PySide6.QtCore import Qt


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

        # Backend selection
        backend_group = QGroupBox("Output Backend")
        backend_layout = QFormLayout()

        self.combo_backend = QComboBox()
        self.combo_backend.addItems(["FileOut (Safe)", "HackRF (Test Setup Only)"])
        backend_layout.addRow("Backend:", self.combo_backend)

        backend_group.setLayout(backend_layout)
        root.addWidget(backend_group)

        # Message configuration
        msg_group = QGroupBox("Message Configuration")
        msg_layout = QFormLayout()

        self.combo_msg_type = QComboBox()
        self.combo_msg_type.addItems([
            "Standard Location (Hex ID)",
            "User Location (GPS)",
            "Test Message",
            "BPSK Pattern (Debug)"
        ])
        msg_layout.addRow("Message Type:", self.combo_msg_type)

        self.beacon_id = QLineEdit("123456789ABCDEF")
        self.beacon_id.setPlaceholderText("15-bit hex beacon ID")
        msg_layout.addRow("Beacon ID (Hex):", self.beacon_id)

        self.lat = QLineEdit("0.0")
        msg_layout.addRow("Latitude:", self.lat)

        self.lon = QLineEdit("0.0")
        msg_layout.addRow("Longitude:", self.lon)

        msg_group.setLayout(msg_layout)
        root.addWidget(msg_group)

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

        self.tx_gain = QSpinBox()
        self.tx_gain.setRange(0, 47)
        self.tx_gain.setValue(10)  # Low default for safety
        self.tx_gain.setSuffix(" dB")
        tx_layout.addRow("TX Gain:", self.tx_gain)

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

    def _start_tx(self):
        """Start 406 MHz transmission (placeholder)."""
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_label.setText("406 MHz signal generation started (placeholder)")

    def _stop_tx(self):
        """Stop transmission (placeholder)."""
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_label.setText("Stopped")

    def _save_profile(self):
        """Save current settings as profile (placeholder)."""
        self.status_label.setText("Save profile: not implemented yet")

    def _load_profile(self):
        """Load profile from file (placeholder)."""
        self.status_label.setText("Load profile: not implemented yet")
