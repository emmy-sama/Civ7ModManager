"""Main application window for the Civilization VII Mod Manager"""

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget

from ..utilities.config import ModManagerPaths
from ..utilities.logging_setup import init_logging
from ..utilities.database import ModDatabase
from ..utilities.constants import (
    APP_VERSION, GITHUB_URL, CIVFANATICS_MOD_URL,
    DEFAULT_WINDOW_SIZE, DEFAULT_NAV_WIDTH, DEFAULT_BUTTON_HEIGHT, MAINFONT
)

from .installed_page import InstalledModsPage
from .get_mods_page import GetModsPage
from .options_page import OptionsPage


class Civ7ModManager(QMainWindow):
    """Main application window for the Civilization VII Mod Manager"""
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Civilization VII Mod Manager v{APP_VERSION}")
        self.setGeometry(100, 100, *DEFAULT_WINDOW_SIZE)
        self.showMaximized()
        self.setFont(MAINFONT)

        # Initialize paths and logging
        self.paths = ModManagerPaths()
        self.logger = init_logging(self.paths.logs_path)
        self.db = ModDatabase(self.paths.db_path)

        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Create Navigation Area (left side)
        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)
        nav_widget.setFixedWidth(DEFAULT_NAV_WIDTH)

        # Create navigation buttons
        self.nav_button_group = [
            QPushButton("Installed Mods"),
            QPushButton("Get Mods"),
            QPushButton("Options"),
        ]
        self.nav_installed = self.nav_button_group[0]
        self.nav_get_mods = self.nav_button_group[1]
        self.nav_options = self.nav_button_group[2]

        for button in self.nav_button_group:
            button.setFixedHeight(DEFAULT_BUTTON_HEIGHT)
            nav_layout.addWidget(button)

        self.link_buttons = [QPushButton("GitHub"), QPushButton("CivFanatics")]
        self.nav_git = self.link_buttons[0]
        self.nav_civfan = self.link_buttons[1]

        nav_layout.addStretch()
        for button in self.link_buttons:
            button.setFixedHeight(DEFAULT_BUTTON_HEIGHT)
            nav_layout.addWidget(button)

        # Create Content Area (right side)
        self.content_area = QStackedWidget()

        # Initialize pages
        self.installed_page = InstalledModsPage(self.paths, self.db)
        self.get_mods_page = GetModsPage(self.paths, self.db)
        self.options_page = OptionsPage(self.paths, self.db)

        self.content_area.addWidget(self.installed_page)
        self.content_area.addWidget(self.get_mods_page)
        self.content_area.addWidget(self.options_page)

        # Connect page change signal
        self.content_area.currentChanged.connect(self._on_page_changed)

        # Connect navigation signals
        self.nav_installed.clicked.connect(
            lambda: self.content_area.setCurrentWidget(self.installed_page))
        self.nav_get_mods.clicked.connect(
            lambda: self.content_area.setCurrentWidget(self.get_mods_page))
        self.nav_options.clicked.connect(
            lambda: self.content_area.setCurrentWidget(self.options_page))
        self.nav_git.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(GITHUB_URL)))
        self.nav_civfan.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(CIVFANATICS_MOD_URL)))

        # Add widgets to main layout
        main_layout.addWidget(nav_widget)
        main_layout.addWidget(self.content_area)

    def _on_page_changed(self, index: int) -> None:
        """Handle page changes in the stacked widget"""
        current_widget = self.content_area.widget(index)
        if current_widget is self.installed_page:
            self.installed_page.refresh()
        elif current_widget is self.get_mods_page:
            if self.get_mods_page.online_mods_table.rowCount() == 0:
                _ = self.get_mods_page.refresh_table()
