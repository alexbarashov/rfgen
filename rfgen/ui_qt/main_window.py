from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QListWidget, QStackedWidget, QListWidgetItem, QStatusBar
)
from PySide6.QtCore import Qt
from .pages.page_quick import PageQuick
from .pages.page_profiles import PageProfiles
from .pages.page_signal_lab import PageSignalLab
from .pages.page_scheduler import PageScheduler
from .pages.page_logs import PageLogs

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("rfgen — Universal RF Generator (PySide6)")
        self.resize(1100, 720)

        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.addItem(QListWidgetItem("Quick TX"))
        self.sidebar.addItem(QListWidgetItem("Profiles"))
        self.sidebar.addItem(QListWidgetItem("Signal Lab"))
        self.sidebar.addItem(QListWidgetItem("Scheduler"))
        self.sidebar.addItem(QListWidgetItem("Logs"))

        self.pages = QStackedWidget()
        self.page_quick = PageQuick(self)
        self.page_profiles = PageProfiles()
        self.page_signal_lab = PageSignalLab()
        self.page_scheduler = PageScheduler()
        self.page_logs = PageLogs()

        self.pages.addWidget(self.page_quick)
        self.pages.addWidget(self.page_profiles)
        self.pages.addWidget(self.page_signal_lab)
        self.pages.addWidget(self.page_scheduler)
        self.pages.addWidget(self.page_logs)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)
        layout.addWidget(self.sidebar, 0)
        layout.addWidget(self.pages, 1)

        self.setCentralWidget(container)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Idle — select a page to start.")

        self.sidebar.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.sidebar.setCurrentRow(0)
