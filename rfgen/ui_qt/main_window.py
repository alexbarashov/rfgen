from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QListWidget, QStackedWidget, QListWidgetItem, QStatusBar
)
from PySide6.QtCore import Qt
from .pages.page_gen_basic import PageGenBasic
from .pages.page_ais import PageAIS
from .pages.page_406 import Page406
from .pages.page_dsc_vhf import PageDSC_VHF
from .pages.page_dsc_hf import PageDSC_HF
from .pages.page_navtex import PageNAVTEX
from .pages.page_121 import Page121
from .pages.page_profiles import PageProfiles
from .pages.page_logs import PageLogs

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("rfgen — Universal RF Generator (PySide6)")
        self.resize(1100, 720)

        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.addItem(QListWidgetItem("Basic"))
        self.sidebar.addItem(QListWidgetItem("AIS"))
        self.sidebar.addItem(QListWidgetItem("406 MHz"))
        self.sidebar.addItem(QListWidgetItem("DSC VHF"))
        self.sidebar.addItem(QListWidgetItem("DSC HF"))
        self.sidebar.addItem(QListWidgetItem("NAVTEX"))
        self.sidebar.addItem(QListWidgetItem("121.5 MHz"))
        self.sidebar.addItem(QListWidgetItem("Profiles"))
        self.sidebar.addItem(QListWidgetItem("Logs"))

        self.pages = QStackedWidget()
        self.page_gen_basic = PageGenBasic(self)
        self.page_ais = PageAIS(self)
        self.page_406 = Page406(self)
        self.page_dsc_vhf = PageDSC_VHF(self)
        self.page_dsc_hf = PageDSC_HF(self)
        self.page_navtex = PageNAVTEX(self)
        self.page_121 = Page121(self)
        self.page_profiles = PageProfiles()
        self.page_logs = PageLogs()

        self.pages.addWidget(self.page_gen_basic)
        self.pages.addWidget(self.page_ais)
        self.pages.addWidget(self.page_406)
        self.pages.addWidget(self.page_dsc_vhf)
        self.pages.addWidget(self.page_dsc_hf)
        self.pages.addWidget(self.page_navtex)
        self.pages.addWidget(self.page_121)
        self.pages.addWidget(self.page_profiles)
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
