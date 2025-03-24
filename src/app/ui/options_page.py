"""Options page for the Civilization VII Mod Manager"""
from pathlib import Path
import shutil
import sqlite3
from PySide6.QtWidgets import (
    QLabel, QPushButton, QVBoxLayout, QGroupBox, QMessageBox
)

from ..utilities.config import ModManagerPaths
from ..utilities.database import ModDatabase

from . import BasePage

class OptionsPage(BasePage):
    """Options configuration page"""
    def __init__(self, path_manager: ModManagerPaths, database: ModDatabase):
        super().__init__(None)
        self.paths = path_manager
        self.db = database
        self.game_mods_path = path_manager.game_mods_path
        self.storage_path = path_manager.storage_path  
        self.logs_path = path_manager.logs_path
        self._init_ui()
        self._update_path_labels()

    def set_paths(self, game_mods_path: Path, storage_path: Path, logs_path: Path) -> None:
        """Set the paths to display in the options page"""
        self.game_mods_path = game_mods_path
        self.storage_path = storage_path
        self.logs_path = logs_path
        self._update_path_labels()

    def _init_ui(self) -> None:
        """Initialize the UI components"""
        # Add title
        title = QLabel("Options")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        self._layout.addWidget(title)

        # Game paths section
        self.paths_group = QGroupBox("Game Paths")
        paths_layout = QVBoxLayout()

        self.game_path_label = QLabel("Game Mods Directory: Not Set")
        self.storage_path_label = QLabel("Mod Storage: Not Set")
        paths_layout.addWidget(self.game_path_label)
        paths_layout.addWidget(self.storage_path_label)
        self.paths_group.setLayout(paths_layout)
        self._layout.addWidget(self.paths_group)

        # Add spacer
        self._layout.addSpacing(20)

        # Logging options section
        logging_group = QGroupBox("Logging")
        logging_layout = QVBoxLayout()

        self.log_path_label = QLabel("Log Directory: Not Set")
        clear_logs_btn = QPushButton("Clear Log Files")
        clear_logs_btn.clicked.connect(self._clear_log_files)

        logging_layout.addWidget(self.log_path_label)
        logging_layout.addWidget(clear_logs_btn)
        logging_group.setLayout(logging_layout)
        self._layout.addWidget(logging_group)

        # Add spacer
        self._layout.addSpacing(20)

        # Mod Management section
        mod_management_group = QGroupBox("Mod Management")
        mod_management_layout = QVBoxLayout()

        uninstall_all_btn = QPushButton("Uninstall All Mods")
        uninstall_all_btn.clicked.connect(self._uninstall_all_mods)
        uninstall_all_btn.setStyleSheet("background-color: #ff4444; color: white;")
        mod_management_layout.addWidget(uninstall_all_btn)

        mod_management_group.setLayout(mod_management_layout)
        self._layout.addWidget(mod_management_group)

        # Add stretch to push content to top
        self._layout.addStretch()

    def _update_path_labels(self) -> None:
        """Update the path labels with current values"""
        if self.game_mods_path:
            self.game_path_label.setText(f"Game Mods Directory: {self.game_mods_path}")
        if self.storage_path:
            self.storage_path_label.setText(f"Mod Storage: {self.storage_path}")
        if self.logs_path:
            self.log_path_label.setText(f"Log Directory: {self.logs_path}")

    def _clear_log_files(self) -> None:
        """Clear all log files from the logs directory"""
        if not self.logs_path:
            return

        try:
            for log_file in self.logs_path.glob("*.log"):
                log_file.unlink()
            self.logger.info("Cleared all log files")
            QMessageBox.information(
                self, "Success", "All log files have been cleared.", 
                QMessageBox.StandardButton.Ok)
        except (OSError, IOError) as e:
            error_msg = f"Failed to clear log files: {str(e)}"
            self.logger.error(error_msg)
            QMessageBox.critical(self, "Error", error_msg, 
                               QMessageBox.StandardButton.Ok)

    def _uninstall_all_mods(self) -> None:
        """Uninstall all mods from storage and database"""
        if not self.storage_path or not self.db:
            return

        reply = QMessageBox.warning(
            self,
            "Confirm Uninstall All",
            "Are you sure you want to uninstall ALL mods? This action cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            # Get list of all mods before removing from database
            mods = self.db.get_all_installed_mods()
            mod_count = len(mods)
            
            # Remove all mods from storage
            if self.storage_path.exists():
                for item in self.storage_path.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()

            # Remove all mods from database
            for mod in mods:
                self.db.remove_installed_mod(mod['mod_id'])

            self.logger.info("Successfully uninstalled %d mods", mod_count)
            QMessageBox.information(
                self, 
                "Success", 
                f"Successfully uninstalled {mod_count} mods",
                QMessageBox.StandardButton.Ok
            )

        except (OSError, IOError, sqlite3.Error) as e:
            error_msg = f"Failed to uninstall all mods: {str(e)}"
            self.logger.error(error_msg)
            QMessageBox.critical(
                self, 
                "Error", 
                error_msg,
                QMessageBox.StandardButton.Ok
            )