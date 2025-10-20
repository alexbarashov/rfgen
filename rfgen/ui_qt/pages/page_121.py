"""121.5 MHz Emergency Locator Beacon signal generator page."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout, QPushButton,
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QGroupBox, QLabel
)
from PySide6.QtCore import Qt


class Page121(QWidget):
    """121.5 MHz Emergency Locator Beacon signal generator page.

    Features:
    - 121.5 MHz frequency (aviation emergency)
    - AM modulation with swept or continuous tone
    - Configurable sweep parameters
    - Test mode for beacon simulation
    - WARNING: Use only in shielded test environment
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)

        # Header with warning
        header = QLabel("<b>121.5 MHz Emergency Beacon Generator</b>")
        header.setStyleSheet("font-size: 14pt;")
        root.addWidget(header)

        warning = QLabel("⚠️ <b>WARNING:</b> 121.5 MHz is an international aviation emergency frequency. "
                        "Only use in shielded test environment. Unauthorized transmission is illegal.")
        warning.setStyleSheet("color: red; background: #fff3cd; padding: 8px; border-radius: 4px;")
        warning.setWordWrap(True)
        root.addWidget(warning)

        # Signal type
        sig_group = QGroupBox("Signal Configuration")
        sig_layout = QFormLayout()

        self.combo_signal_type = QComboBox()
        self.combo_signal_type.addItems([
            "Swept Tone (300-1600 Hz)",
            "Continuous Tone",
            "Modulated Carrier (CW)"
        ])
        sig_layout.addRow("Signal Type:", self.combo_signal_type)
        self.combo_signal_type.currentTextChanged.connect(self._on_signal_type_changed)

        sig_group.setLayout(sig_layout)
        root.addWidget(sig_group)

        # Tone parameters
        tone_group = QGroupBox("Tone Parameters")
        tone_layout = QFormLayout()

        self.tone_hz = QSpinBox()
        self.tone_hz.setRange(100, 3000)
        self.tone_hz.setValue(1000)
        self.tone_hz.setSuffix(" Hz")
        tone_layout.addRow("Tone Frequency:", self.tone_hz)

        self.sweep_rate = QDoubleSpinBox()
        self.sweep_rate.setRange(0.1, 10.0)
        self.sweep_rate.setValue(2.0)
        self.sweep_rate.setSuffix(" Hz/s")
        self.sweep_rate.setDecimals(1)
        tone_layout.addRow("Sweep Rate:", self.sweep_rate)

        self.sweep_low = QSpinBox()
        self.sweep_low.setRange(100, 3000)
        self.sweep_low.setValue(300)
        self.sweep_low.setSuffix(" Hz")
        tone_layout.addRow("Sweep Low:", self.sweep_low)

        self.sweep_high = QSpinBox()
        self.sweep_high.setRange(100, 3000)
        self.sweep_high.setValue(1600)
        self.sweep_high.setSuffix(" Hz")
        tone_layout.addRow("Sweep High:", self.sweep_high)

        tone_group.setLayout(tone_layout)
        root.addWidget(tone_group)

        # Modulation parameters
        mod_group = QGroupBox("Modulation Parameters")
        mod_layout = QFormLayout()

        self.am_depth = QDoubleSpinBox()
        self.am_depth.setRange(0.0, 1.0)
        self.am_depth.setValue(0.8)
        self.am_depth.setSingleStep(0.1)
        self.am_depth.setDecimals(2)
        mod_layout.addRow("AM Depth:", self.am_depth)

        self.duty_cycle = QDoubleSpinBox()
        self.duty_cycle.setRange(0.1, 1.0)
        self.duty_cycle.setValue(1.0)
        self.duty_cycle.setSingleStep(0.1)
        self.duty_cycle.setDecimals(2)
        mod_layout.addRow("Duty Cycle:", self.duty_cycle)

        mod_group.setLayout(mod_layout)
        root.addWidget(mod_group)

        # TX settings
        tx_group = QGroupBox("Transmission Settings")
        tx_layout = QFormLayout()

        self.target_hz = QLineEdit("121500000")
        self.target_hz.setEnabled(False)
        tx_layout.addRow("Target Frequency (Hz):", self.target_hz)

        self.tx_gain = QSpinBox()
        self.tx_gain.setRange(0, 47)
        self.tx_gain.setValue(10)  # Low default for safety
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
        self.status_label = QLabel("Ready - Configure signal and use only in shielded environment")
        root.addWidget(self.status_label)

        root.addStretch()

        # Initialize UI state
        self._on_signal_type_changed(self.combo_signal_type.currentText())

    def _on_signal_type_changed(self, text):
        """Enable/disable controls based on signal type."""
        is_sweep = "Swept" in text
        is_tone = "Tone" in text

        self.tone_hz.setEnabled(not is_sweep and is_tone)
        self.sweep_rate.setEnabled(is_sweep)
        self.sweep_low.setEnabled(is_sweep)
        self.sweep_high.setEnabled(is_sweep)
        self.am_depth.setEnabled(is_tone)
        self.duty_cycle.setEnabled(is_tone)

    def _start_tx(self):
        """Start 121.5 MHz transmission (placeholder)."""
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_label.setText("121.5 MHz transmission started (placeholder)")

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
