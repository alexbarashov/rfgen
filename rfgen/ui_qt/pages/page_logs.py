"""Logs viewer and system diagnostics page."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLabel, QComboBox, QGroupBox, QMessageBox,
    QCheckBox
)
from PySide6.QtCore import Qt, QTimer
from pathlib import Path
import sys
import subprocess
import shutil
import platform

from ...utils.paths import logs_dir, pkg_root


class PageLogs(QWidget):
    """Logs viewer and diagnostics page.

    Features:
    - View logs from rfgen/logs/
    - System diagnostics (Python version, HackRF utilities, processes)
    - Auto-refresh/tail mode
    - Clear logs with confirmation
    - Open logs folder in Explorer
    - Kill all hackrf_transfer processes
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)

        # Header
        header = QLabel("<b>Logs & Diagnostics</b>")
        header.setStyleSheet("font-size: 14pt;")
        root.addWidget(header)

        # Diagnostics panel
        diag_group = QGroupBox("System Diagnostics")
        diag_layout = QVBoxLayout()

        self.diag_text = QLabel()
        self.diag_text.setStyleSheet("font-family: 'Consolas', monospace; font-size: 9pt;")
        self.diag_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.diag_text.setWordWrap(True)
        diag_layout.addWidget(self.diag_text)

        btn_refresh_diag = QPushButton("Refresh Diagnostics")
        btn_refresh_diag.clicked.connect(self._refresh_diagnostics)
        diag_layout.addWidget(btn_refresh_diag)

        diag_group.setLayout(diag_layout)
        root.addWidget(diag_group)

        # Log viewer
        log_group = QGroupBox("Log Viewer")
        log_layout = QVBoxLayout()

        # Log file selection
        file_row = QHBoxLayout()
        file_row.addWidget(QLabel("Log file:"))

        self.combo_log = QComboBox()
        self.combo_log.currentTextChanged.connect(self._on_log_changed)
        file_row.addWidget(self.combo_log, 1)

        btn_refresh_list = QPushButton("Refresh List")
        btn_refresh_list.clicked.connect(self._refresh_log_list)
        file_row.addWidget(btn_refresh_list)

        log_layout.addLayout(file_row)

        # Log content viewer
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("Select a log file to view...")
        self.log_text.setStyleSheet("font-family: 'Consolas', monospace; font-size: 9pt;")
        log_layout.addWidget(self.log_text)

        # Tail mode
        tail_row = QHBoxLayout()
        self.chk_tail = QCheckBox("Auto-refresh (tail mode)")
        self.chk_tail.toggled.connect(self._toggle_tail)
        tail_row.addWidget(self.chk_tail)

        self.tail_lines = QComboBox()
        self.tail_lines.addItems(["50 lines", "100 lines", "200 lines", "All"])
        self.tail_lines.setCurrentText("100 lines")
        tail_row.addWidget(QLabel("Show:"))
        tail_row.addWidget(self.tail_lines)
        tail_row.addStretch()

        log_layout.addLayout(tail_row)

        log_group.setLayout(log_layout)
        root.addWidget(log_group)

        # Action buttons
        btn_layout = QHBoxLayout()

        btn_open_folder = QPushButton("Open Logs Folder")
        btn_open_folder.clicked.connect(self._open_logs_folder)
        btn_layout.addWidget(btn_open_folder)

        btn_kill_hackrf = QPushButton("Kill All hackrf_transfer")
        btn_kill_hackrf.clicked.connect(self._kill_hackrf_processes)
        btn_layout.addWidget(btn_kill_hackrf)

        btn_clear_logs = QPushButton("Clear Logs...")
        btn_clear_logs.clicked.connect(self._clear_logs)
        btn_clear_logs.setStyleSheet("background-color: #ffcccc;")
        btn_layout.addWidget(btn_clear_logs)

        btn_layout.addStretch()

        root.addLayout(btn_layout)

        # Status
        self.status_label = QLabel("Ready")
        root.addWidget(self.status_label)

        # Timer for auto-refresh
        self.tail_timer = QTimer()
        self.tail_timer.timeout.connect(self._refresh_log_content)
        self.tail_timer.setInterval(1000)  # 1 second

        # Initial refresh
        self._refresh_diagnostics()
        self._refresh_log_list()

    def _refresh_diagnostics(self):
        """Refresh system diagnostics information."""
        lines = []

        # Python version
        lines.append(f"Python: {sys.version.split()[0]} ({platform.platform()})")

        # rfgen package location
        lines.append(f"rfgen: {pkg_root()}")

        # Logs directory
        lines.append(f"Logs dir: {logs_dir()}")

        # HackRF utilities
        hackrf_info = shutil.which("hackrf_info")
        hackrf_transfer = shutil.which("hackrf_transfer")

        if hackrf_info:
            lines.append(f"hackrf_info: {hackrf_info}")
        else:
            lines.append("hackrf_info: NOT FOUND in PATH")

        if hackrf_transfer:
            lines.append(f"hackrf_transfer: {hackrf_transfer}")
        else:
            lines.append("hackrf_transfer: NOT FOUND in PATH")

        # Running hackrf_transfer processes
        running = self._get_hackrf_processes()
        if running:
            lines.append(f"\nRunning hackrf_transfer processes: {len(running)}")
            for pid, cmd in running[:5]:  # Show first 5
                lines.append(f"  PID {pid}: {cmd}")
            if len(running) > 5:
                lines.append(f"  ... and {len(running) - 5} more")
        else:
            lines.append("\nNo hackrf_transfer processes running")

        self.diag_text.setText("\n".join(lines))
        self.status_label.setText("Diagnostics refreshed")

    def _get_hackrf_processes(self):
        """Get list of running hackrf_transfer processes."""
        processes = []
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ['tasklist', '/FI', 'IMAGENAME eq hackrf_transfer.exe', '/FO', 'CSV', '/NH'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                for line in result.stdout.strip().split('\n'):
                    if 'hackrf_transfer' in line.lower():
                        parts = line.replace('"', '').split(',')
                        if len(parts) >= 2:
                            processes.append((parts[1].strip(), parts[0].strip()))
            else:
                result = subprocess.run(
                    ['pgrep', '-a', 'hackrf_transfer'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split(None, 1)
                        if len(parts) >= 2:
                            processes.append((parts[0], parts[1]))
        except Exception:
            pass
        return processes

    def _refresh_log_list(self):
        """Refresh list of log files."""
        self.combo_log.clear()

        ldir = logs_dir()
        log_files = sorted(ldir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)

        if not log_files:
            self.combo_log.addItem("(no logs found)")
            self.status_label.setText("No log files found")
            return

        for log_file in log_files:
            self.combo_log.addItem(log_file.name)

        self.status_label.setText(f"Found {len(log_files)} log file(s)")

    def _on_log_changed(self, filename):
        """Load and display selected log file."""
        if not filename or filename == "(no logs found)":
            self.log_text.clear()
            return

        self._refresh_log_content()

    def _refresh_log_content(self):
        """Refresh log content from currently selected file."""
        filename = self.combo_log.currentText()
        if not filename or filename == "(no logs found)":
            return

        log_path = logs_dir() / filename
        if not log_path.exists():
            self.log_text.setPlainText("(file not found)")
            return

        try:
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()

            # Apply tail limit
            tail_text = self.tail_lines.currentText()
            if tail_text == "All":
                content = "".join(lines)
            else:
                limit = int(tail_text.split()[0])
                content = "".join(lines[-limit:])

            self.log_text.setPlainText(content)

            # Auto-scroll to bottom
            if self.chk_tail.isChecked():
                cursor = self.log_text.textCursor()
                cursor.movePosition(cursor.End)
                self.log_text.setTextCursor(cursor)

        except Exception as e:
            self.log_text.setPlainText(f"Error reading log: {e}")

    def _toggle_tail(self, enabled):
        """Enable/disable tail mode."""
        if enabled:
            self.tail_timer.start()
            self.status_label.setText("Tail mode enabled (auto-refresh every 1s)")
        else:
            self.tail_timer.stop()
            self.status_label.setText("Tail mode disabled")

    def _open_logs_folder(self):
        """Open logs folder in system file explorer."""
        ldir = logs_dir()
        try:
            if platform.system() == "Windows":
                subprocess.run(['explorer', str(ldir)])
            elif platform.system() == "Darwin":
                subprocess.run(['open', str(ldir)])
            else:
                subprocess.run(['xdg-open', str(ldir)])
            self.status_label.setText(f"Opened: {ldir}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to open folder:\n{e}")

    def _kill_hackrf_processes(self):
        """Kill all running hackrf_transfer processes."""
        processes = self._get_hackrf_processes()

        if not processes:
            QMessageBox.information(self, "Kill Processes", "No hackrf_transfer processes running")
            return

        reply = QMessageBox.question(
            self,
            "Kill Processes",
            f"Kill {len(processes)} hackrf_transfer process(es)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        killed = 0
        errors = []

        for pid, cmd in processes:
            try:
                if platform.system() == "Windows":
                    subprocess.run(['taskkill', '/PID', str(pid), '/F', '/T'],
                                 check=True, capture_output=True)
                else:
                    subprocess.run(['kill', '-9', str(pid)],
                                 check=True, capture_output=True)
                killed += 1
            except Exception as e:
                errors.append(f"PID {pid}: {e}")

        msg = f"Killed {killed} process(es)"
        if errors:
            msg += f"\n\nErrors:\n" + "\n".join(errors[:5])

        QMessageBox.information(self, "Kill Processes", msg)
        self._refresh_diagnostics()

    def _clear_logs(self):
        """Clear all log files with confirmation."""
        ldir = logs_dir()
        log_files = list(ldir.glob("*.log"))

        if not log_files:
            QMessageBox.information(self, "Clear Logs", "No log files to clear")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Clear Logs",
            f"Delete {len(log_files)} log file(s)?\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        deleted = 0
        errors = []

        for log_file in log_files:
            try:
                log_file.unlink()
                deleted += 1
            except Exception as e:
                errors.append(f"{log_file.name}: {e}")

        msg = f"Deleted {deleted} log file(s)"
        if errors:
            msg += f"\n\nErrors:\n" + "\n".join(errors[:5])

        QMessageBox.information(self, "Clear Logs", msg)
        self._refresh_log_list()
        self.log_text.clear()
        self.status_label.setText(f"Cleared {deleted} log file(s)")
