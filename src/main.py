import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QTreeWidget, QLabel, QPushButton, QHBoxLayout,
    QFileDialog, QMessageBox, QMenu, QInputDialog, 
    QProgressBar, QPlainTextEdit, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6 import QtCore

from archive import ArchiveHandler
from modinfo import ModInfo
from ui_components import ModTreeItem

import shutil

class Civ7ModManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Civilization VII Mod Manager")
        self.setGeometry(100, 100, 1200, 800)
        
        # Define paths
        local_appdata = os.getenv('LOCALAPPDATA')
        if not local_appdata:
            raise EnvironmentError("Unable to locate LOCALAPPDATA")

        self.app_path = Path(__file__).parent
        self.game_mods_path = Path(local_appdata) / "Firaxis Games" / "Sid Meier's Civilization VII" / "Mods"
        self.storage_path = Path(local_appdata) / "Civ7ModManager" / "ModStorage"
        self.profiles_path = Path(local_appdata) / "Civ7ModManager" / "Profiles"
        self.logs_path = Path(local_appdata) / "Civ7ModManager" / "Logs"
        self.lib_path = self.app_path / "lib"
        self.mods = {}
        
        # Create necessary directories
        for path in [self.game_mods_path, self.storage_path, self.profiles_path, self.logs_path]:
            path.mkdir(parents=True, exist_ok=True)

        # Main widget and layout setup
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Add path info
        game_path_label = QLabel(f"Game Mods Directory: {self.game_mods_path}")
        storage_path_label = QLabel(f"Mod Storage: {self.storage_path}")
        layout.addWidget(game_path_label)
        layout.addWidget(storage_path_label)
        
        # Add mod count label
        self.mod_count_label = QLabel("Mods: 0 total, 0 enabled")
        layout.addWidget(self.mod_count_label)
        
        # Initialize and setup mod tree widget
        self.mod_tree = QTreeWidget()
        headers = ["Name", "Mod ID", "Version", "Affects Saves", "Has Conflicts", "Author"]
        self.mod_tree.setHeaderLabels(headers)
        self.mod_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents) # type: ignore
        self.mod_tree.header().setSectionsClickable(True) # type: ignore
        self.mod_tree.header().sectionClicked.connect(self._handle_sort) # type: ignore
        self.mod_tree.setAlternatingRowColors(True)
        self.mod_tree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.mod_tree.customContextMenuRequested.connect(self._show_context_menu)
        self.mod_tree.itemChanged.connect(self._on_mod_toggle)
        layout.addWidget(self.mod_tree)
        
        # Add progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Add log viewer
        log_label = QLabel("Operation Log:")
        layout.addWidget(log_label)
        self.log_viewer = QPlainTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setMaximumHeight(150)
        layout.addWidget(self.log_viewer)
        
        # Set up logging first
        self._setup_logging()
        
        # Set up remaining class attributes
        self.archive_filter = "Mod Archives (*.zip *.7z *.rar *.r00);;All Files (*.*)"
        self._current_sort_column = 0
        self._current_sort_order = Qt.SortOrder.AscendingOrder
        
        # Buttons layout
        button_layout = QHBoxLayout()
        
        # Add buttons
        refresh_button = QPushButton("Refresh Mod List")
        install_button = QPushButton("Install Mod")
        save_profile_button = QPushButton("Save Profile")
        load_profile_button = QPushButton("Load Profile")
        deploy_button = QPushButton("Deploy Mods")
        deploy_button.setStyleSheet("background-color: #4CAF50; color: white;")
        clear_log_button = QPushButton("Clear Log")
        
        # Connect button signals
        refresh_button.clicked.connect(self.refresh_mod_list)
        install_button.clicked.connect(self.install_mod)
        save_profile_button.clicked.connect(self.save_profile)
        load_profile_button.clicked.connect(self.load_profile)
        deploy_button.clicked.connect(self.deploy_mods)
        clear_log_button.clicked.connect(self.log_viewer.clear)
        
        # Add buttons to layout
        for button in [refresh_button, install_button, save_profile_button, 
                      load_profile_button, deploy_button, clear_log_button]:
            button_layout.addWidget(button)
        
        layout.addLayout(button_layout)
        
        # Initial mod list population
        self.refresh_mod_list()

    def _setup_logging(self):
        """Setup logging configuration"""
        self.logger = logging.getLogger('Civ7ModManager')
        self.logger.setLevel(logging.INFO)
        
        # File handler
        log_file = self.logs_path / f"modmanager_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)
        
        # Custom handler for GUI log viewer
        class QtLogHandler(logging.Handler):
            def __init__(self, log_widget):
                super().__init__()
                self.log_widget = log_widget
            
            def emit(self, record):
                msg = self.format(record)
                self.log_widget.appendPlainText(msg)
        
        qt_handler = QtLogHandler(self.log_viewer)
        qt_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))  # Fixed typo in levelname
        self.logger.addHandler(qt_handler)

    def _handle_sort(self, column):
        """Handle column header clicks for sorting"""
        if self._current_sort_column == column:
            # Toggle sort order if clicking the same column
            self._current_sort_order = Qt.SortOrder.DescendingOrder if self._current_sort_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
        else:
            self._current_sort_column = column
            self._current_sort_order = Qt.SortOrder.AscendingOrder
        
        self.mod_tree.sortItems(column, self._current_sort_order)

    def _update_mod_count(self):
        """Update the mod count display"""
        total_mods = len(self.mods)
        enabled_mods = sum(1 for mod in self.mods.values() if mod.enabled)
        self.mod_count_label.setText(f"Mods: {total_mods} total, {enabled_mods} enabled")

    def _on_mod_toggle(self, item, column):
        """Handle mod enable/disable checkbox changes"""
        if column == 0:  # Only handle changes in the Name column
            is_enabled = item.checkState(0) == Qt.CheckState.Checked
            folder_name = item.data(0, Qt.ItemDataRole.UserRole)  # Store folder_name in item data
            
            if folder_name in self.mods:
                self.mods[folder_name].enabled = is_enabled
                self._update_mod_count()
                self._update_conflicts()

    def _update_conflicts(self):
        """Update the conflicts status for all mods"""
        enabled_mods = {name: mod for name, mod in self.mods.items() if mod.enabled}
        
        # Clear all conflict statuses
        for i in range(self.mod_tree.topLevelItemCount()):
            item = self.mod_tree.topLevelItem(i)
            item.setText(4, '')
            
        # Check for conflicts between enabled mods
        for i in range(self.mod_tree.topLevelItemCount()):
            item = self.mod_tree.topLevelItem(i)
            mod_name = item.text(0)
            mod = self.mods.get(mod_name)
            
            if not mod:
                continue
                
            has_conflicts = False
            if mod.enabled:
                for other_name, other_mod in enabled_mods.items():
                    if other_name != mod_name:
                        if mod.metadata['affected_files'] & other_mod.metadata['affected_files']:
                            has_conflicts = True
                            break
            
            item.setText(4, 'Yes' if has_conflicts else 'No')

    def deploy_mods(self):
        """Deploy enabled mods to game directory"""
        try:
            # Ask for confirmation
            reply = QMessageBox.question(
                self,
                "Confirm Deploy",
                "This will clear the game's mod folder and copy all enabled mods. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                return
            
            enabled_mods = [(name, mod) for name, mod in self.mods.items() if mod.enabled]
            total_mods = len(enabled_mods)
            
            if total_mods == 0:
                self.logger.info("No mods are enabled for deployment")
                QMessageBox.information(self, "Deploy Complete", "No mods are enabled.")
                return
            
            self.logger.info(f"Starting deployment of {total_mods} mods")
            self.progress_bar.setMaximum(total_mods + 1)  # +1 for cleanup
            self.progress_bar.setValue(0)
            self.progress_bar.show()
            
            # Clear game mods directory
            self.logger.info("Clearing game mods directory")
            if self.game_mods_path.exists():
                for item in self.game_mods_path.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
            
            self.progress_bar.setValue(1)
            
            # Copy enabled mods to game directory
            for i, (name, mod) in enumerate(enabled_mods, 2):
                self.logger.info(f"Deploying mod: {name}")
                shutil.copytree(mod.path, self.game_mods_path / name)
                self.progress_bar.setValue(i)
            
            success_msg = f"Successfully deployed {total_mods} mod{'s' if total_mods != 1 else ''} to game directory"
            self.logger.info(success_msg)
            QMessageBox.information(self, "Deploy Complete", success_msg)
            
        except Exception as e:
            error_msg = f"Failed to deploy mods: {str(e)}"
            self.logger.error(error_msg)
            QMessageBox.critical(self, "Deploy Error", error_msg)
        finally:
            self.progress_bar.hide()

    def refresh_mod_list(self):
        """Refresh the list of mods from storage directory"""
        self.logger.info("Refreshing mod list")
        self.mod_tree.clear()
        self.mods.clear()
        
        if not self.storage_path.exists():
            self.logger.warning("Storage directory not found!")
            self._update_mod_count()
            return
            
        try:
            # Count total mods first
            mod_dirs = [d for d in self.storage_path.iterdir() if d.is_dir()]
            total_mods = len(mod_dirs)
            
            if total_mods > 0:
                self.progress_bar.setMaximum(total_mods)
                self.progress_bar.setValue(0)
                self.progress_bar.show()
            
            # Sort mod directories by name
            mod_dirs.sort(key=lambda x: x.name.lower())
            
            for i, mod_item in enumerate(mod_dirs):
                try:
                    mod_info = ModInfo(mod_item)
                    self.mods[mod_info.folder_name] = mod_info
                    
                    tree_item = ModTreeItem(mod_info)
                    tree_item.setData(0, Qt.ItemDataRole.UserRole, mod_info.folder_name)  # Store folder_name for reference
                    self.mod_tree.addTopLevelItem(tree_item)
                    
                    self.logger.info(f"Loaded mod: {mod_info.folder_name}")
                    self.progress_bar.setValue(i + 1)
                except Exception as mod_error:
                    self.logger.error(f"Error loading mod {mod_item.name}: {str(mod_error)}")
                    
            # Update conflicts after all mods are loaded
            self._update_conflicts()
            
            # Sort by current sort column and order
            self.mod_tree.sortItems(self._current_sort_column, self._current_sort_order)
                    
        except Exception as e:
            error_msg = f"Error reading mods: {str(e)}"
            self.logger.error(error_msg)
        finally:
            self.progress_bar.hide()
            self._update_mod_count()

    def install_mod(self):
        """Install a new mod from an archive file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Mod Archive",
            "",
            self.archive_filter
        )
        
        if not file_path:
            return
            
        try:
            self.logger.info(f"Installing mod from: {file_path}")
            
            # Get archive type and check support
            archive_type = ArchiveHandler.get_archive_type(file_path)
            if not ArchiveHandler.is_format_supported(archive_type):
                error_msg = f"Archive format '{archive_type}' is not supported.\n\n"
                if archive_type == 'rar':
                    error_msg += "Please ensure UnRAR.dll is present in the lib folder."
                elif archive_type == '7z':
                    error_msg += "Please ensure py7zr is installed correctly."
                raise ValueError(error_msg)
            
            self.progress_bar.setMaximum(3)  # 3 steps: validate, extract, refresh
            self.progress_bar.setValue(0)
            self.progress_bar.show()
            self.progress_bar.setValue(1)
            
            # Extract the mod folder
            self.logger.info("Extracting mod folder")
            try:
                mod_name = ArchiveHandler.extract_mod_folder(file_path, self.storage_path)
                if not mod_name:
                    raise ValueError("Could not determine mod folder name")
                
                self.logger.info(f"Mod extracted as: {mod_name}")
                self.progress_bar.setValue(2)
                
                QMessageBox.information(self, "Success", f"Mod '{mod_name}' installed successfully!")
                self.refresh_mod_list()
                self.progress_bar.setValue(3)
                
            except Exception as extract_error:
                # If extraction fails, ensure cleanup of any partial files
                if 'mod_name' in locals() and mod_name and (self.storage_path / mod_name).exists():
                    shutil.rmtree(self.storage_path / mod_name)
                raise extract_error
            
        except ValueError as ve:
            error_msg = str(ve)
            self.logger.error(f"Validation error: {error_msg}")
            QMessageBox.critical(self, "Error", error_msg)
        except Exception as e:
            error_msg = f"Failed to install mod: {str(e)}"
            self.logger.error(error_msg)
            QMessageBox.critical(self, "Error", error_msg)
        finally:
            self.progress_bar.hide()

    def save_profile(self):
        """Save current mod configuration as a profile"""
        name, ok = QInputDialog.getText(self, "Save Profile", "Enter profile name:")
        if ok and name:
            try:
                self.logger.info(f"Saving profile: {name}")
                # Get current mod states using folder_name as key
                profile_data = {
                    folder_name: mod.enabled
                    for folder_name, mod in self.mods.items()
                }
                
                profile_path = self.profiles_path / f"{name}.json"
                with open(profile_path, 'w') as f:
                    json.dump(profile_data, f, indent=2)
                    
                success_msg = f"Profile '{name}' saved successfully!"
                self.logger.info(success_msg)
                QMessageBox.information(self, "Success", success_msg)
            except Exception as e:
                error_msg = f"Failed to save profile: {str(e)}"
                self.logger.error(error_msg)
                QMessageBox.critical(self, "Error", error_msg)

    def load_profile(self):
        """Load a saved mod profile"""
        profiles = [p.stem for p in self.profiles_path.glob("*.json")]
        if not profiles:
            self.logger.info("No profiles found")
            QMessageBox.information(self, "No Profiles", "No saved profiles found.")
            return
            
        # Sort profiles alphabetically
        profiles.sort(key=str.lower)
            
        name, ok = QInputDialog.getItem(
            self,
            "Load Profile",
            "Select profile:",
            profiles,
            editable=False
        )
        
        if ok and name:
            try:
                self.logger.info(f"Loading profile: {name}")
                # Load profile data
                profile_path = self.profiles_path / f"{name}.json"
                with open(profile_path, 'r') as f:
                    profile_data = json.load(f)
                
                # Update tree items and mod states
                root = self.mod_tree.invisibleRootItem()
                for i in range(root.childCount()):
                    item = root.child(i)
                    folder_name = item.data(0, Qt.ItemDataRole.UserRole)
                    if folder_name in profile_data:
                        should_be_enabled = profile_data[folder_name]
                        item.setCheckState(0, Qt.CheckState.Checked if should_be_enabled else Qt.CheckState.Unchecked)
                        self.mods[folder_name].enabled = should_be_enabled
                
                # Update conflict status after loading profile
                self._update_conflicts()
                self._update_mod_count()
                
                success_msg = f"Profile '{name}' loaded successfully!"
                self.logger.info(success_msg)
                QMessageBox.information(self, "Success", success_msg)
            except Exception as e:
                error_msg = f"Failed to load profile: {str(e)}"
                self.logger.error(error_msg)
                QMessageBox.critical(self, "Error", error_msg)

    def _show_context_menu(self, position):
        """Show context menu for mod tree items"""
        item = self.mod_tree.itemAt(position)
        if not item:
            return
            
        menu = QMenu()
        view_info_action = menu.addAction("View Mod Info")
        view_conflicts_action = menu.addAction("Check Conflicts")
        uninstall_action = menu.addAction("Uninstall")
        
        action = menu.exec(self.mod_tree.viewport().mapToGlobal(position))
        
        folder_name = item.data(0, Qt.ItemDataRole.UserRole)
        if action == view_info_action:
            self._show_mod_info(folder_name)
        elif action == view_conflicts_action:
            self._check_conflicts(folder_name)
        elif action == uninstall_action:
            self._uninstall_mod(folder_name)

    def _show_mod_info(self, folder_name):
        """Display mod information"""
        mod = self.mods.get(folder_name)
        if not mod:
            return
            
        info_text = f"Mod Name: {mod.metadata['display_name']}\n"
        info_text += f"Folder: {folder_name}\n"
        info_text += f"ID: {mod.metadata['id']}\n"
        info_text += f"Version: {mod.metadata['version']}\n"
        info_text += f"Authors: {mod.metadata['authors']}\n"
        info_text += f"Status: {'Enabled' if mod.enabled else 'Disabled'}\n"
        info_text += f"Location: {mod.path}\n"
        info_text += f"Affects Saved Games: {'Yes' if mod.metadata['affects_saves'] else 'No'}\n\n"
        
        if mod.metadata['dependencies']:
            info_text += "Dependencies:\n"
            for dep in mod.metadata['dependencies']:
                info_text += f"- {dep['title']} ({dep['id']})\n"
            info_text += "\n"
        
        if mod.metadata['affected_files']:
            info_text += "Affected Files:\n"
            for file in sorted(mod.metadata['affected_files']):
                info_text += f"- {file}\n"
        
        QMessageBox.information(self, f"Mod Information - {mod.metadata['display_name']}", info_text)

    def _check_conflicts(self, folder_name):
        """Check for conflicts with other enabled mods"""
        mod = self.mods.get(folder_name)
        if not mod:
            return
            
        conflicts = []
        for other_folder, other_mod in self.mods.items():
            if other_folder != folder_name and other_mod.enabled:
                # Check for overlapping affected files
                common_files = mod.metadata['affected_files'] & other_mod.metadata['affected_files']
                if common_files:
                    conflicts.append(f"{other_mod.metadata['display_name']}:\n" + "\n".join(f"  - {file}" for file in sorted(common_files)))
        
        if conflicts:
            QMessageBox.warning(
                self,
                "Mod Conflicts",
                f"Conflicts found for {mod.metadata['display_name']} with enabled mods:\n\n" + "\n".join(conflicts)
            )
        else:
            QMessageBox.information(
                self,
                "Mod Conflicts",
                f"No conflicts found for {mod.metadata['display_name']} with enabled mods"
            )

    def _uninstall_mod(self, folder_name):
        """Uninstall a mod by removing it from storage"""
        mod = self.mods.get(folder_name)
        if not mod:
            return
            
        reply = QMessageBox.question(
            self,
            "Confirm Uninstall",
            f"Are you sure you want to uninstall '{mod.metadata['display_name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.logger.info(f"Uninstalling mod: {folder_name}")
                # Remove from storage
                shutil.rmtree(mod.path)
                success_msg = f"Mod '{mod.metadata['display_name']}' uninstalled successfully!"
                self.logger.info(success_msg)
                QMessageBox.information(self, "Success", success_msg)
                self.refresh_mod_list()
            except Exception as e:
                error_msg = f"Failed to uninstall mod: {str(e)}"
                self.logger.error(error_msg)
                QMessageBox.critical(self, "Error", error_msg)

def main():
    app = QApplication(sys.argv)
    window = Civ7ModManager()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()