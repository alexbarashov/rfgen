"""DSC VHF (Digital Selective Calling) signal generator page."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout, QPushButton,
    QComboBox, QLineEdit, QSpinBox, QGroupBox, QLabel
)
from PySide6.QtCore import Qt


class PageDSC_VHF(QWidget):
    """DSC VHF signal generator page.

    Features:
    - Channel 70 (156.525 MHz)
    - FSK modulation (170 Hz shift, 100 Bd)
    - Distress, urgency, safety, routine calls
    - ITU-R M.493 compliance
    - Test mode with patterns
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)

        # Header
        header = QLabel("<b>DSC VHF Signal Generator (Ch 70)</b>")
        header.setStyleSheet("font-size: 14pt;")
        root.addWidget(header)

        # Channel info
        info = QLabel("📡 Channel 70: 156.525 MHz | FSK: 100 Bd, ±85 Hz")
        info.setStyleSheet("background: #e3f2fd; padding: 6px; border-radius: 4px;")
        root.addWidget(info)

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

        self.mmsi_from = QLineEdit("123456789")
        call_layout.addRow("MMSI (From):", self.mmsi_from)

        self.mmsi_to = QLineEdit("987654321")
        call_layout.addRow("MMSI (To):", self.mmsi_to)

        call_group.setLayout(call_layout)
        root.addWidget(call_group)

        # Message configuration
        msg_group = QGroupBox("Message Details")
        msg_layout = QFormLayout()

        self.combo_nature = QComboBox()
        self.combo_nature.addItems([
            "Fire/Explosion",
            "Flooding",
            "Collision",
            "Grounding",
            "Listing",
            "Sinking",
            "Disabled and Adrift",
            "Undesignated",
            "Abandoning Ship",
            "Piracy/Armed Robbery",
            "Man Overboard"
        ])
        msg_layout.addRow("Nature of Distress:", self.combo_nature)

        self.position = QLineEdit("0000.00N/00000.00E")
        msg_layout.addRow("Position:", self.position)

        self.utc_time = QLineEdit("0000")
        msg_layout.addRow("UTC Time (HHMM):", self.utc_time)

        msg_group.setLayout(msg_layout)
        root.addWidget(msg_group)

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

    def _start_tx(self):
        """Start DSC VHF transmission (placeholder)."""
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_label.setText("DSC VHF transmission started (placeholder)")

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
