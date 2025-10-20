"""NAVTEX signal generator page."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout, QPushButton,
    QComboBox, QLineEdit, QSpinBox, QGroupBox, QLabel, QTextEdit, QFileDialog
)
from PySide6.QtCore import Qt


class PageNAVTEX(QWidget):
    """NAVTEX signal generator page.

    Features:
    - 518 kHz and 490 kHz frequencies
    - SITOR-B encoding (FEC mode)
    - FSK modulation (170 Hz shift, 100 Bd)
    - Text message input or file import
    - Station ID and message type
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)

        # Header
        header = QLabel("<b>NAVTEX Signal Generator</b>")
        header.setStyleSheet("font-size: 14pt;")
        root.addWidget(header)

        # Frequency selection
        freq_group = QGroupBox("Frequency")
        freq_layout = QFormLayout()

        self.combo_freq = QComboBox()
        self.combo_freq.addItems([
            "518 kHz (International)",
            "490 kHz (National)",
            "4209.5 kHz (HF)",
            "Custom"
        ])
        freq_layout.addRow("Frequency:", self.combo_freq)

        self.target_hz = QLineEdit("518000")
        self.target_hz.setEnabled(False)
        freq_layout.addRow("Target (Hz):", self.target_hz)

        self.combo_freq.currentTextChanged.connect(self._on_freq_changed)

        freq_group.setLayout(freq_layout)
        root.addWidget(freq_group)

        # Message configuration
        msg_group = QGroupBox("Message Configuration")
        msg_layout = QFormLayout()

        self.station_id = QLineEdit("A")
        self.station_id.setMaxLength(1)
        self.station_id.setPlaceholderText("A-Z")
        msg_layout.addRow("Station ID:", self.station_id)

        self.msg_type = QLineEdit("A")
        self.msg_type.setMaxLength(1)
        self.msg_type.setPlaceholderText("A=Navigational Warning, B=Met, etc.")
        msg_layout.addRow("Message Type:", self.msg_type)

        self.msg_number = QLineEdit("01")
        self.msg_number.setMaxLength(2)
        msg_layout.addRow("Message Number:", self.msg_number)

        msg_group.setLayout(msg_layout)
        root.addWidget(msg_group)

        # Message text
        text_group = QGroupBox("Message Text")
        text_layout = QVBoxLayout()

        self.message_text = QTextEdit()
        self.message_text.setPlaceholderText("Enter NAVTEX message text here...\n\n"
                                            "Max 80 characters per line.\n"
                                            "SITOR-B encoding will be applied.")
        self.message_text.setMaximumHeight(150)
        text_layout.addWidget(self.message_text)

        btn_import = QPushButton("Import from File...")
        btn_import.clicked.connect(self._import_text)
        text_layout.addWidget(btn_import)

        text_group.setLayout(text_layout)
        root.addWidget(text_group)

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
        if "518 kHz" in text:
            self.target_hz.setText("518000")
            self.target_hz.setEnabled(False)
        elif "490 kHz" in text:
            self.target_hz.setText("490000")
            self.target_hz.setEnabled(False)
        elif "4209.5 kHz" in text:
            self.target_hz.setText("4209500")
            self.target_hz.setEnabled(False)
        elif "Custom" in text:
            self.target_hz.setEnabled(True)

    def _import_text(self):
        """Import message text from file (placeholder)."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import NAVTEX Message",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                    self.message_text.setPlainText(text)
                    self.status_label.setText(f"Imported: {file_path}")
            except Exception as e:
                self.status_label.setText(f"Import failed: {e}")

    def _start_tx(self):
        """Start NAVTEX transmission (placeholder)."""
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_label.setText("NAVTEX transmission started (placeholder)")

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
