import sys
import os
import json
import zipfile
import py7zr
import rarfile
import shutil
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QTreeWidget, QTreeWidgetItem, QLabel, QPushButton, QHBoxLayout,
    QFileDialog, QMessageBox, QMenu, QInputDialog, 
    QProgressBar, QPlainTextEdit, QHeaderView
)
from PyQt6.QtCore import Qt, QSize
from PyQt6 import QtCore

class ArchiveHandler:
    """Handles different types of archive files"""
    
    @staticmethod
    def get_archive_type(file_path):
        """Determine the type of archive based on file extension"""
        ext = Path(file_path).suffix.lower()
        if ext == '.zip':
            return 'zip'
        elif ext == '.7z':
            return '7z'
        elif ext in ['.rar', '.r00']:
            return 'rar'
        else:
            raise ValueError(f"Unsupported archive format: {ext}")
    
    @staticmethod
    def list_files(file_path):
        """List all files in the archive"""
        archive_type = ArchiveHandler.get_archive_type(file_path)
        
        if archive_type == 'zip':
            with zipfile.ZipFile(file_path, 'r') as archive:
                return archive.namelist()
        elif archive_type == '7z':
            with py7zr.SevenZipFile(file_path, 'r') as archive:
                return [str(f) for f in archive.getnames()]
        elif archive_type == 'rar':
            with rarfile.RarFile(file_path, 'r') as archive:
                return archive.namelist()
    
    @staticmethod
    def extract_all(file_path, extract_path):
        """Extract all files from the archive"""
        archive_type = ArchiveHandler.get_archive_type(file_path)
        
        if archive_type == 'zip':
            with zipfile.ZipFile(file_path, 'r') as archive:
                archive.extractall(extract_path)
        elif archive_type == '7z':
            with py7zr.SevenZipFile(file_path, 'r') as archive:
                archive.extractall(extract_path)
        elif archive_type == 'rar':
            with rarfile.RarFile(file_path, 'r') as archive:
                archive.extractall(extract_path)

class ModInfo:
    def __init__(self, mod_path):
        self.path = Path(mod_path)
        self.name = self.path.name
        self.enabled = False
        self.metadata = {
            'id': '',
            'version': '',
            'name': '',
            'description': '',
            'authors': '',
            'affects_saves': False,
            'dependencies': [],
            'affected_files': set()
        }
        self._load_metadata()

    def _load_metadata(self):
        """Load metadata from .modinfo file"""
        # Look for .modinfo file in the mod directory
        modinfo_files = list(self.path.glob("*.modinfo"))
        if not modinfo_files:
            print(f"No .modinfo file found for {self.name}")
            return

        try:
            tree = ET.parse(modinfo_files[0])
            root = tree.getroot()
            
            # Get basic mod info
            self.metadata['id'] = root.get('id', '')
            self.metadata['version'] = root.get('version', '')
            
            # Get properties
            properties = root.find('.//Properties')
            if properties is not None:
                self.metadata['name'] = self._get_element_text(properties, 'Name')
                self.metadata['description'] = self._get_element_text(properties, 'Description')
                self.metadata['authors'] = self._get_element_text(properties, 'Authors')
                affects_saves = self._get_element_text(properties, 'AffectsSavedGames')
                self.metadata['affects_saves'] = affects_saves == '1' if affects_saves else False
            
            # Get dependencies
            dependencies = root.find('.//Dependencies')
            if dependencies is not None:
                for dep in dependencies.findall('Mod'):
                    self.metadata['dependencies'].append({
                        'id': dep.get('id', ''),
                        'title': dep.get('title', '')
                    })
            
            # Get affected files
            for action_group in root.findall('.//ActionGroup'):
                for action in action_group.findall('.//Actions'):
                    # UI Scripts
                    for script in action.findall('.//UIScripts/Item'):
                        if script.text:
                            self.metadata['affected_files'].add(script.text)
                    
                    # Localization files
                    for text_file in action.findall('.//LocalizedText/File'):
                        if text_file.text:
                            self.metadata['affected_files'].add(text_file.text)

        except Exception as e:
            print(f"Error loading metadata for {self.name}: {e}")

    def _get_element_text(self, parent, tag):
        """Helper method to safely get element text"""
        element = parent.find(tag)
        return element.text if element is not None else ''

class ModTreeItem(QTreeWidgetItem):
    def __init__(self, mod_info):
        super().__init__()
        self.mod_info = mod_info
        self.update_display()
        
    def update_display(self):
        """Update the item's display text"""
        # Column order: Name, ModID, Version, Affects Saves, Has Conflicts, Author
        self.setText(0, self.mod_info.name)
        self.setText(1, self.mod_info.metadata['id'])
        self.setText(2, self.mod_info.metadata['version'])
        self.setText(3, 'Yes' if self.mod_info.metadata['affects_saves'] else 'No')
        self.setText(4, '')  # Conflicts will be updated later
        self.setText(5, self.mod_info.metadata['authors'])
        
        self.setCheckState(0, Qt.CheckState.Checked if self.mod_info.enabled else Qt.CheckState.Unchecked)

class Civ7ModManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Civilization VII Mod Manager")
        self.setGeometry(100, 100, 1200, 800)  # Made window wider for columns
        
        # Check archive handlers
        self._validate_archive_handlers()
        
        # Define paths
        self.game_mods_path = Path(os.getenv('LOCALAPPDATA')) / "Firaxis Games" / "Sid Meier's Civilization VII" / "Mods"
        self.storage_path = Path(os.getenv('APPDATA')) / "Civ7ModManager" / "ModStorage"
        self.profiles_path = Path(os.getenv('APPDATA')) / "Civ7ModManager" / "Profiles"
        self.logs_path = Path(os.getenv('APPDATA')) / "Civ7ModManager" / "Logs"
        self.mods = {}
        
        # Create necessary directories
        for path in [self.game_mods_path, self.storage_path, self.profiles_path, self.logs_path]:
            path.mkdir(parents=True, exist_ok=True)
        
        # Main widget and layout
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
        
        # Create mod tree widget instead of list widget
        self.mod_tree = QTreeWidget()
        self.mod_tree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.mod_tree.customContextMenuRequested.connect(self._show_context_menu)
        self.mod_tree.itemChanged.connect(self._on_mod_toggle)
        
        # Set up columns
        headers = ["Name", "Mod ID", "Version", "Affects Saves", "Has Conflicts", "Author"]
        self.mod_tree.setHeaderLabels(headers)
        self.mod_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.mod_tree.header().setSectionsClickable(True)
        self.mod_tree.header().sectionClicked.connect(self._handle_sort)
        self.mod_tree.setAlternatingRowColors(True)
        
        # Replace mod_list with mod_tree in layout
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
        self._setup_logging()
        
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

        # Update file dialog filter for install_mod
        self.archive_filter = "Mod Archives (*.zip *.7z *.rar *.r00);;All Files (*.*)"

        # Track sort order
        self._current_sort_column = 0
        self._current_sort_order = Qt.SortOrder.AscendingOrder

    def _validate_archive_handlers(self):
        """Check if required archive handlers are available"""
        missing_handlers = []
        
        # Check RAR support
        
        
        # Check 7z support
        try:
            if not py7zr.is_7zfile("nonexistent.7z"):  # Just checking if the module works
                pass
        except Exception:
            missing_handlers.append("7-Zip (needed for .7z files)")
        
        if missing_handlers:
            msg = "Some archive formats may not be supported. Please install:\n\n"
            msg += "\n".join(f"- {handler}" for handler in missing_handlers)
            msg += "\n\nZIP files will still work normally."
            QMessageBox.warning(self, "Missing Dependencies", msg)

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
        qt_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
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
            mod_name = item.text(0)
            
            if mod_name in self.mods:
                self.mods[mod_name].enabled = is_enabled
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
                    self.mods[mod_item.name] = mod_info
                    
                    tree_item = ModTreeItem(mod_info)
                    self.mod_tree.addTopLevelItem(tree_item)
                    
                    self.logger.info(f"Loaded mod: {mod_item.name}")
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
            self.progress_bar.setMaximum(4)  # 4 steps: read archive, validate, extract, refresh
            self.progress_bar.setValue(0)
            self.progress_bar.show()
            
            # Get all files in the archive
            self.logger.info("Reading archive contents")
            all_files = ArchiveHandler.list_files(file_path)
            self.progress_bar.setValue(1)
            
            # Look for .modinfo files
            modinfo_files = [f for f in all_files if f.endswith('.modinfo')]
            
            if not modinfo_files:
                raise ValueError("No .modinfo file found in the archive")
            
            # Get the correct mod directory name
            modinfo_path = modinfo_files[0]
            parts = Path(modinfo_path).parts
            
            # If modinfo is in a subfolder, use that as the mod name
            if len(parts) > 1:
                mod_name = parts[0]
            else:
                # Get top level directories
                top_level_dirs = {Path(item).parts[0] for item in all_files if '/' in item or '\\' in item}
                if not top_level_dirs:
                    raise ValueError("Invalid mod structure")
                mod_name = top_level_dirs.pop()
            
            self.progress_bar.setValue(2)
            mod_path = self.storage_path / mod_name
            
            # If mod already exists, ask for confirmation to overwrite
            if mod_path.exists():
                self.logger.info(f"Mod {mod_name} already exists, asking for confirmation")
                reply = QMessageBox.question(
                    self,
                    "Mod Already Exists",
                    f"Mod '{mod_name}' already exists. Do you want to overwrite it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
                
                # Remove existing mod from storage
                self.logger.info(f"Removing existing mod: {mod_name}")
                shutil.rmtree(mod_path)
            
            # Extract the mod to storage
            self.logger.info(f"Extracting mod to: {mod_path}")
            try:
                ArchiveHandler.extract_all(file_path, self.storage_path)
                self.progress_bar.setValue(3)
                
                self.logger.info(f"Mod '{mod_name}' installed successfully")
                QMessageBox.information(self, "Success", f"Mod '{mod_name}' installed successfully!")
                
                self.refresh_mod_list()
                self.progress_bar.setValue(4)
            except rarfile.BadRarFile:
                raise ValueError("Failed to extract RAR file. Please ensure WinRAR or unrar is installed on your system.")
            
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
                # Get current mod states
                profile_data = {
                    mod_name: mod.enabled
                    for mod_name, mod in self.mods.items()
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
                    mod_name = item.text(0)
                    if mod_name in profile_data:
                        should_be_enabled = profile_data[mod_name]
                        item.setCheckState(0, Qt.CheckState.Checked if should_be_enabled else Qt.CheckState.Unchecked)
                        self.mods[mod_name].enabled = should_be_enabled
                
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
        
        mod_name = item.text(0)
        if action == view_info_action:
            self._show_mod_info(mod_name)
        elif action == view_conflicts_action:
            self._check_conflicts(mod_name)
        elif action == uninstall_action:
            self._uninstall_mod(mod_name)

    def _show_mod_info(self, mod_name):
        """Display mod information"""
        mod = self.mods.get(mod_name)
        if not mod:
            return
            
        info_text = f"Mod Name: {mod.metadata['name'] or mod_name}\n"
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
        
        QMessageBox.information(self, f"Mod Information - {mod_name}", info_text)

    def _check_conflicts(self, mod_name):
        """Check for conflicts with other enabled mods"""
        mod = self.mods.get(mod_name)
        if not mod:
            return
            
        conflicts = []
        for other_name, other_mod in self.mods.items():
            if other_name != mod_name and other_mod.enabled:
                # Check for overlapping affected files
                common_files = mod.metadata['affected_files'] & other_mod.metadata['affected_files']
                if common_files:
                    conflicts.append(f"{other_name}:\n" + "\n".join(f"  - {file}" for file in sorted(common_files)))
        
        if conflicts:
            QMessageBox.warning(
                self,
                "Mod Conflicts",
                f"Conflicts found for {mod_name} with enabled mods:\n\n" + "\n".join(conflicts)
            )
        else:
            QMessageBox.information(
                self,
                "Mod Conflicts",
                f"No conflicts found for {mod_name} with enabled mods"
            )

    def _uninstall_mod(self, mod_name):
        """Uninstall a mod by removing it from storage"""
        reply = QMessageBox.question(
            self,
            "Confirm Uninstall",
            f"Are you sure you want to uninstall '{mod_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            mod = self.mods.get(mod_name)
            if not mod:
                return
                
            try:
                self.logger.info(f"Uninstalling mod: {mod_name}")
                # Remove from storage
                shutil.rmtree(mod.path)
                success_msg = f"Mod '{mod_name}' uninstalled successfully!"
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