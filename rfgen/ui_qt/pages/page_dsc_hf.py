"""DSC HF (Digital Selective Calling) signal generator page."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout, QPushButton,
    QComboBox, QLineEdit, QSpinBox, QGroupBox, QLabel
)
from PySide6.QtCore import Qt


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
            "16804.5 kHz",
            "Custom"
        ])
        freq_layout.addRow("Frequency:", self.combo_freq)

        self.target_hz = QLineEdit("2187500")
        self.target_hz.setEnabled(False)
        freq_layout.addRow("Target (Hz):", self.target_hz)

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

        self.tx_gain = QSpinBox()
        self.tx_gain.setRange(0, 47)
        self.tx_gain.setValue(30)
        self.tx_gain.setSuffix(" dB")
        tx_layout.addRow("TX Gain:", self.tx_gain)

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
                self.target_hz.setText(value)
                self.target_hz.setEnabled(False)
                return

        if "Custom" in text:
            self.target_hz.setEnabled(True)

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

    def _save_profile(self):
        """Save current settings as profile (placeholder)."""
        self.status_label.setText("Save profile: not implemented yet")

    def _load_profile(self):
        """Load profile from file (placeholder)."""
        self.status_label.setText("Load profile: not implemented yet")
