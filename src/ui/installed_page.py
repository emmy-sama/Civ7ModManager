"""Installed mods page for the Civilization VII Mod Manager"""
import os
import shutil
from pathlib import Path
from typing import Callable
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QProgressBar, QHeaderView, QMessageBox,
    QStatusBar, QFrame, QMenu, QWidget
)

from utilities.config import ModManagerPaths
from utilities.database import ModDatabase, ModCount
from utilities.constants import APP_VERSION, DEFAULT_ICON_SIZE, DEFAULT_BUTTON_HEIGHT
from ui.ui_components import ModTableItem

from . import BasePage


class InstalledModsPage(BasePage):
    """Page showing installed mods and their management"""

    def __init__(self, path_manager: ModManagerPaths, database: ModDatabase):
        super().__init__(None)
        self.db = database
        self._current_sort_column = 0
        self._current_sort_order = Qt.SortOrder.AscendingOrder
        self.game_mods_path = path_manager.game_mods_path
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the UI components"""
        # Tables layout
        tables_layout = QHBoxLayout()

        # Disabled mods table
        disabled_section = QVBoxLayout()
        disabled_label = QLabel("Disabled Mods")
        disabled_section.addWidget(disabled_label)

        self.disabled_table = self._create_mod_table()
        disabled_section.addWidget(self.disabled_table)
        tables_layout.addLayout(disabled_section)

        # Add vertical separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        tables_layout.addWidget(separator)

        # Enabled mods table
        enabled_section = QVBoxLayout()
        enabled_label = QLabel("Enabled Mods")
        enabled_section.addWidget(enabled_label)

        self.enabled_table = self._create_mod_table()
        enabled_section.addWidget(self.enabled_table)
        tables_layout.addLayout(enabled_section)

        self._layout.addLayout(tables_layout)

        # Add progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        self._layout.addWidget(self.progress_bar)

        # Buttons layout
        button_layout = QHBoxLayout()

        # Add buttons
        refresh_button = QPushButton("Refresh Mod List")
        enable_all_button = QPushButton("Enable All")
        disable_all_button = QPushButton("Disable All")
        deploy_button = QPushButton("Deploy Mods")
        deploy_button.setStyleSheet("background-color: #4CAF50; color: white;")

        # Set button heights
        for button in [refresh_button, enable_all_button, disable_all_button, deploy_button]:
            button.setFixedHeight(DEFAULT_BUTTON_HEIGHT)

        # Connect button signals
        refresh_button.clicked.connect(self.refresh)
        enable_all_button.clicked.connect(self.enable_all_mods)
        disable_all_button.clicked.connect(self.disable_all_mods)
        deploy_button.clicked.connect(self.deploy_mods)

        # Add buttons to layout
        for button in [
            refresh_button,
            enable_all_button,
            disable_all_button,
            deploy_button,
        ]:
            button_layout.addWidget(button)

        self._layout.addLayout(button_layout)

        # Add status bar
        status_layout = QHBoxLayout()

        # Status message (stretches to fill space)
        self.status_bar = QStatusBar()
        status_layout.addWidget(self.status_bar, 1)

        # Add mod count label
        self.mod_count_label = QLabel("Mods: 0 Enabled | 0 Installed")
        status_layout.addWidget(self.mod_count_label)

        # Update section with version
        update_layout = QHBoxLayout()
        check_updates_btn = QPushButton("Check for Updates")
        check_updates_btn.setFixedHeight(DEFAULT_BUTTON_HEIGHT)
        check_updates_btn.clicked.connect(self._check_for_updates)
        version_label = QLabel(f" v{APP_VERSION}")
        update_layout.addWidget(version_label)
        update_layout.addWidget(check_updates_btn)

        # Add update section to status layout
        status_layout.addLayout(update_layout)

        self._layout.addLayout(status_layout)

        self.refresh()

    def _create_mod_table(self) -> QTableWidget:
        """Create and configure a mod table widget"""
        table = QTableWidget()
        table.setSortingEnabled(True)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(pos, table))
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(DEFAULT_ICON_SIZE + 4)

        # Column headers
        headers = ["Name", "Authors", "Version", "Affects Saves"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)

        # Set header font and style
        header = table.horizontalHeader()
        header_font = header.font()
        header_font.setPointSize(10)
        header_font.setBold(True)
        header.setFont(header_font)
        
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setMinimumSectionSize(100)

        # Column sizes
        header.resizeSection(0, 325)  # Combined icon + name
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.resizeSection(1, 150)  # Authors
        header.resizeSection(2, 100)  # Version
        header.resizeSection(3, 100)  # Affects Saves

        return table

    def refresh(self) -> None:
        """Refresh the list of installed mods"""
        if not self.db:
            return

        self.logger.info("Refreshing mod list")
        self.enabled_table.clearContents()
        self.enabled_table.setRowCount(0)
        self.disabled_table.clearContents()
        self.disabled_table.setRowCount(0)

        mods = self.db.get_all_installed_mods()
        enabled_mods = [mod for mod in mods if mod.get('enabled', False)]
        disabled_mods = [mod for mod in mods if not mod.get('enabled', False)]

        self._populate_table(self.enabled_table, enabled_mods)
        self._populate_table(self.disabled_table, disabled_mods)
        self._update_mod_count()

    def _populate_table(self, table: QTableWidget, mods: list) -> None:
        """Populate a table with mod data"""
        for row, mod in enumerate(mods):
            table.insertRow(row)

            # Load icon image
            pixmap = QPixmap()
            web_id = mod.get('web_id')
            if web_id:
                icon_data = self.db.get_mod_icon(web_id)
                if icon_data:
                    pixmap.loadFromData(icon_data)
            if pixmap.isNull():
                # Fallback to default icon
                default_icon_path = Path(__file__).parent.parent.parent / "assets" / "default_icon.png"
                if default_icon_path.exists():
                    pixmap.load(str(default_icon_path))
            if not pixmap.isNull():
                pixmap = pixmap.scaled(DEFAULT_ICON_SIZE, DEFAULT_ICON_SIZE,
                                     Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)

            # Create combined icon and name widget
            combined_widget = QWidget()
            combined_layout = QHBoxLayout(combined_widget)
            combined_layout.setContentsMargins(4, 2, 4, 2)
            combined_layout.setSpacing(8)

            # Icon label
            icon_label = QLabel()
            icon_label.setPixmap(pixmap)
            icon_label.setMinimumSize(DEFAULT_ICON_SIZE, DEFAULT_ICON_SIZE)
            icon_label.setMaximumSize(DEFAULT_ICON_SIZE, DEFAULT_ICON_SIZE)
            combined_layout.addWidget(icon_label)

            # Name label
            name_label = QLabel(mod.get('display_name', ''))
            combined_layout.addWidget(name_label)
            combined_layout.addStretch()

            table.setCellWidget(row, 0, combined_widget)

            # Other columns
            table.setItem(row, 1, QTableWidgetItem(mod.get('authors', '')))
            table.setItem(row, 2, QTableWidgetItem(mod.get('version', '')))

            affects_saves = bool(mod.get('affects_saves'))
            affects_saves_text = 'Yes' if affects_saves else 'No' if affects_saves is not None else ''
            table.setItem(row, 3, QTableWidgetItem(affects_saves_text))

            # Check for conflicts
            if table == self.enabled_table:  # Only check conflicts for enabled mods
                has_conflicts = self._check_mod_conflicts(mod)
                if has_conflicts:
                    # Set background color to light red for the entire row
                    for col in range(table.columnCount()):
                        item = table.item(row, col)
                        if item:
                            item.setBackground(Qt.GlobalColor.red)
                        # Also color the combined widget cell
                        if col == 0:
                            combined_widget.setStyleSheet("background-color: red;")

    def _check_mod_conflicts(self, mod: dict) -> bool:
        """Check if a mod has conflicts with other enabled mods
        
        Args:
            mod: The mod to check for conflicts
            
        Returns:
            True if the mod has conflicts, False otherwise
        """
        # Get all enabled mods except this one
        enabled_mods = [m for m in self.db.get_all_enabled_mods() 
                       if m.get('mod_id') != mod.get('mod_id')]
        
        # Get this mod's affected files
        mod_files = set()
        affected_files = mod.get('affected_files', {})
        if affected_files:
            # Check UIScripts files
            ui_scripts = affected_files.get('ui_scripts', set())
            if ui_scripts:
                mod_files.update(ui_scripts)
                
            # Check ImportFiles files
            import_files = affected_files.get('import_files', set())
            if import_files:
                mod_files.update(import_files)
        
        # Check each enabled mod for conflicts
        for other_mod in enabled_mods:
            other_files = set()
            other_affected = other_mod.get('affected_files', {})
            if other_affected:
                # Get other mod's UIScripts files
                other_ui = other_affected.get('ui_scripts', set())
                if other_ui:
                    other_files.update(other_ui)
                    
                # Get other mod's ImportFiles files
                other_imports = other_affected.get('import_files', set())
                if other_imports:
                    other_files.update(other_imports)
            
            # If there's any overlap in the files, we have a conflict
            if mod_files & other_files:
                return True
                
        return False

    def _check_for_updates(self) -> None:
        """Placeholder for update check functionality"""
        self.status_bar.showMessage("Update check not implemented yet")

    def _update_mod_count(self) -> None:
        """Update the mod count display"""
        if not self.db:
            return

        mod_count: ModCount = self.db.count_mods()
        self.mod_count_label.setText(
            f"Mods: {mod_count.total} total, {mod_count.enabled} enabled")

    def _update_conflicts(self) -> None:
        """Update the conflicts status for all mods"""
        self.refresh()  # This will recheck conflicts and update row colors

    def _item_changed(self, item: QTableWidgetItem) -> None:
        """Handle mod state changes"""
        if not isinstance(item, ModTableItem):
            return
        try:
            mod_id = item.mod_id
            mod_info = self.db.get_installed_mod(mod_id) if self.db else None
            if not mod_info:
                self.logger.error("Failed to get mod info for %s", mod_id)
                return
            new_state = item.checkState() == Qt.CheckState.Checked
            if new_state != mod_info.get("enabled", False) and self.db:
                self.logger.info("Changing mod state: %s -> %s",
                                 mod_id, "enabled" if new_state else "disabled")
                self.db.set_mod_enabled(mod_id, new_state)
                item.update_display()

            self._update_mod_count()
            self._update_conflicts()

        except (IOError, ValueError, KeyError) as e:
            error_msg = f"Failed to update mod state: {str(e)}"
            self.logger.error(error_msg)
            QMessageBox.critical(self, "Error", error_msg, QMessageBox.StandardButton.Ok)

    def enable_all_mods(self) -> None:
        """Enable all mods"""
        if not self.db:
            return

        self.db.enable_all_mods()
        self._update_mod_count()
        self._update_conflicts()
        self.refresh()

    def disable_all_mods(self) -> None:
        """Disable all mods"""
        if not self.db:
            return

        self.db.disable_all_mods()
        self._update_mod_count()
        self._update_conflicts()
        self.logger.info("All mods disabled")
        self.refresh()

    def deploy_mods(self) -> None:
        """Deploy enabled mods to game directory"""
        if not self.db or not self.game_mods_path:
            return

        try:
            if not self.game_mods_path.exists():
                error_msg = "Game mods directory does not exist"
                self.logger.error(error_msg)
                QMessageBox.critical(self, "Error", error_msg, QMessageBox.StandardButton.Ok)
                return

            reply = QMessageBox.question(
                self,
                "Confirm Deploy",
                "This will clear the game's mod folder and copy all enabled mods to it. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.No:
                return

            enabled_mods = self.db.get_all_enabled_mods()
            total_mods = len(enabled_mods)

            self.logger.info("Starting deployment of %s mods", total_mods)
            self.progress_bar.setMaximum(total_mods + 1)
            self.progress_bar.setValue(0)
            self.progress_bar.show()

            # Clear game mods directory
            self.logger.info("Clearing game mods directory")
            for item in self.game_mods_path.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

            self.progress_bar.setValue(1)

            # Copy enabled mods to game directory
            for mod in enabled_mods:
                self.logger.info("Deploying mod: %s", mod["display_name"])
                shutil.copytree(mod["file_path"],
                                self.game_mods_path / mod["mod_id"])
                self.progress_bar.setValue(self.progress_bar.value() + 1)

            success_msg = f"Successfully deployed {total_mods} mod{'s' if total_mods != 1 else ''}"
            self.logger.info(success_msg)
            QMessageBox.information(self, "Deploy Complete", success_msg, QMessageBox.StandardButton.Ok)

        except (IOError, OSError) as e:
            error_msg = f"Failed to deploy mods: {str(e)}"
            self.logger.error(error_msg)
            QMessageBox.critical(self, "Deploy Error", error_msg, QMessageBox.StandardButton.Ok)
        finally:
            self.progress_bar.hide()

    def handle_exceptions(self, function: Callable, path: str, excinfo) -> None:
        """Handle exceptions during file operations by removing read-only attribute"""
        path_obj = Path(path)
        if not path_obj.exists():
            return

        os.chmod(path_obj, 128)
        path_obj.unlink()

    def _show_context_menu(self, position: QPoint, table: QTableWidget) -> None:
        """Show the context menu for a mod"""
        item = table.itemAt(position)
        if not item:
            return

        # Get the mod info from the row
        row = table.row(item)
        combined_widget = table.cellWidget(row, 0)
        if not combined_widget:
            return

        # Find the name label within the combined widget
        name_label = None
        for child in combined_widget.children():
            if isinstance(child, QLabel) and child.text():  # Find label with text (not icon)
                name_label = child
                break
        if not name_label:
            return

        global_pos = table.viewport().mapToGlobal(position)

        # Create context menu
        menu = QMenu()

        # Determine if mod is enabled based on which table it's in
        is_enabled = table == self.enabled_table
        toggle_action = menu.addAction("Disable" if is_enabled else "Enable")
        view_info_action = menu.addAction("View Mod Info")
        view_conflicts_action = menu.addAction("View Conflicts")
        goto_location_action = menu.addAction("Go to Mod Location")
        uninstall_action = menu.addAction("Uninstall")

        action = menu.exec(global_pos)
        if not action:
            return

        # Get mod info from database based on name
        mod_name = name_label.text()
        mod_info = next((m for m in self.db.get_all_installed_mods()
                        if m.get('display_name') == mod_name), None)
        if not mod_info:
            return

        mod_id = mod_info.get('mod_id')
        if not mod_id:
            return

        if action == toggle_action:
            self.db.set_mod_enabled(mod_id, not is_enabled)
            self.refresh()
        elif action == view_info_action:
            self._show_mod_info(mod_id)
        elif action == view_conflicts_action:
            self._check_conflicts(mod_id)
        elif action == goto_location_action:
            self._goto_mod_location(mod_id)
        elif action == uninstall_action:
            if QMessageBox.question(
                self,
                "Confirm Uninstall",
                f"Are you sure you want to uninstall {mod_name}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            ) == QMessageBox.StandardButton.Yes:
                try:
                    self.db.remove_installed_mod(mod_id)
                    self.refresh()
                except (IOError, ValueError) as e:
                    error_msg = f"Failed to uninstall mod: {str(e)}"
                    self.logger.error(error_msg)
                    QMessageBox.critical(self, "Error", error_msg, QMessageBox.StandardButton.Ok)

    def _show_mod_info(self, mod_id: str) -> None:
        """Display mod information"""
        mod_info = self.db.get_installed_mod(mod_id)
        if mod_info is None:
            error_msg = f"Mod not found in database: {mod_id}"
            self.logger.error(error_msg)
            QMessageBox.critical(self, "Error", error_msg)
            return

        sections = []

        # Basic Info Section
        basic_info = [
            ("Mod Name", mod_info.get("display_name", "")),
            ("Mod ID", mod_info.get("mod_id", "")),
            ("Version", mod_info.get("version", "")),
            ("Authors", mod_info.get("authors", "")),
            ("Status", "Enabled" if mod_info.get("enabled", "") else "Disabled"),
            ("Location", str(mod_info.get("file_path", ""))),
            ("Affects Saved Games", "Yes" if mod_info.get("affect_saves", "") else "No"),
        ]

        sections.append(
            "Basic Information\n" + "-" * 50 + "\n" +
            "\n".join(f"{key}: {value}" for key, value in basic_info)
        )

        # Dependencies Section
        if mod_info.get("dependencies", ""):
            dep_text = "\n\nDependencies\n" + "-" * 50 + "\n"
            for dep in mod_info.get("dependencies", ""):
                dep_text += f"• {dep['title']} ({dep['mod_id']})\n"
            sections.append(dep_text)

        # Affected Files Section
        if mod_info.get("affected_files", ""):
            files_text = "\nAffected Files\n" + "-" * 50 + "\n"
            for file in sorted(mod_info.get("affected_files", "")):
                files_text += f"• {file}\n"
            sections.append(files_text)

        # Show the info in a larger message box
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(f"Mod Information - {mod_info.get('display_name', '')}")
        msg_box.setText("".join(sections))
        msg_box.setStyleSheet("QLabel{min-width: 600px; min-height: 400px;}")
        msg_box.exec()

    def _goto_mod_location(self, mod_id: str) -> None:
        """Open the mod's folder in File Explorer"""
        path = self.db.get_mod_path(mod_id)
        if not path:
            error_msg = f"Failed to get mod path: {mod_id}"
            self.logger.error(error_msg)
            QMessageBox.critical(self, "Error", error_msg, QMessageBox.StandardButton.Ok)
            return

    def _check_conflicts(self, mod_id: str) -> None:
        """Check for conflicts with other enabled mods"""
        mod_info = self.db.get_installed_mod(mod_id)
        if not mod_info:
            return

        # TODO: Implement conflict checking
        conflicts = []
        if conflicts:
            QMessageBox.warning(
                self,
                "Mod Conflicts",
                f"Conflicts found for {mod_info.get('display_name', '')} with enabled mods:\n\n" +
                "\n".join(conflicts)
            )
        else:
            QMessageBox.information(
                self,
                "Mod Conflicts",
                f"No conflicts found for {mod_info.get('display_name', '')} with enabled mods",
                QMessageBox.StandardButton.Ok
            )
