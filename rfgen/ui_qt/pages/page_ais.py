"""AIS (Automatic Identification System) signal generator page."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout, QPushButton,
    QComboBox, QLineEdit, QSpinBox, QGroupBox, QLabel, QTextEdit
)
from PySide6.QtCore import Qt


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

        # Channel selection
        channel_group = QGroupBox("Channel Configuration")
        channel_layout = QFormLayout()

        self.combo_channel = QComboBox()
        self.combo_channel.addItems(["Channel A (161.975 MHz)", "Channel B (162.025 MHz)", "Custom"])
        channel_layout.addRow("Channel:", self.combo_channel)

        self.target_hz = QLineEdit("162025000")
        self.target_hz.setEnabled(False)
        channel_layout.addRow("Target Frequency (Hz):", self.target_hz)

        self.combo_channel.currentTextChanged.connect(self._on_channel_changed)

        channel_group.setLayout(channel_layout)
        root.addWidget(channel_group)

        # Message configuration
        msg_group = QGroupBox("Message Configuration")
        msg_layout = QFormLayout()

        self.combo_msg_type = QComboBox()
        self.combo_msg_type.addItems(["Position Report (1/2/3)", "Base Station (4)", "Static Data (5)", "Test Pattern"])
        msg_layout.addRow("Message Type:", self.combo_msg_type)

        self.mmsi = QLineEdit("123456789")
        msg_layout.addRow("MMSI:", self.mmsi)

        self.payload_input = QTextEdit()
        self.payload_input.setMaximumHeight(80)
        self.payload_input.setPlaceholderText("Payload (hex or NMEA VDM format)")
        msg_layout.addRow("Payload:", self.payload_input)

        msg_group.setLayout(msg_layout)
        root.addWidget(msg_group)

        # TX settings
        tx_group = QGroupBox("Transmission Settings")
        tx_layout = QFormLayout()

        self.tx_gain = QSpinBox()
        self.tx_gain.setRange(0, 47)
        self.tx_gain.setValue(30)
        self.tx_gain.setSuffix(" dB")
        tx_layout.addRow("TX Gain:", self.tx_gain)

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

    def _on_channel_changed(self, text):
        """Update frequency based on channel selection."""
        if "Channel A" in text:
            self.target_hz.setText("161975000")
            self.target_hz.setEnabled(False)
        elif "Channel B" in text:
            self.target_hz.setText("162025000")
            self.target_hz.setEnabled(False)
        elif "Custom" in text:
            self.target_hz.setEnabled(True)

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

    def _save_profile(self):
        """Save current settings as profile (placeholder)."""
        self.status_label.setText("Save profile: not implemented yet")

    def _load_profile(self):
        """Load profile from file (placeholder)."""
        self.status_label.setText("Load profile: not implemented yet")
