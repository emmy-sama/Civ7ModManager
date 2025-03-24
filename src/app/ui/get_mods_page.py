"""Get mods page for the Civilization VII Mod Manager"""
import tempfile
import shutil
import os
from pathlib import Path
from typing import Dict, Type, Optional
from qasync import asyncSlot

from PySide6.QtCore import Qt, QPoint, QUrl
from PySide6.QtGui import QPixmap, QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QTableWidget, QWidget,
    QTableWidgetItem, QFrame, QComboBox, QMessageBox,
    QStatusBar, QFileDialog, QHeaderView, QMenu,
)

from ..utilities.config import ModManagerPaths
from ..utilities.database import ModDatabase
from ..utilities.providers import CivFanaticsProvider, ParserError
from ..utilities.modinfo_parser import parse_modinfo, ModInfo, ParseError
from .ui_components import StarRatingWidget, ModActionWidget
from ..utilities import archive as Ah

from . import BasePage


class GetModsPage(BasePage):
    """Page for browsing and downloading mods"""

    def __init__(self, path_manager: ModManagerPaths, database: ModDatabase) -> None:
        super().__init__(None)
        self.paths = path_manager
        self.db = database
        self.storage_path = self.paths.storage_path
        self.archive_filter = "Mod Archives (*.zip *.7z *.rar *.r00)"

        # Initialize UI components that are referenced early
        self.online_status_bar = QStatusBar()
        self.provider_combo = None

        # Provider attributes
        self.providers: Dict[str, Type] = {"CivFanatics": CivFanaticsProvider}
        self.current_provider = CivFanaticsProvider()

        # Pagination attributes
        self.current_page = 1
        self.total_pages = 1
        self.is_loading = False
        self._last_scroll_time = 0
        self._scroll_throttle = 0.5

        self.online_mods_table = self._init_mods_table()
        self._init_ui()
        self._get_mods_initialized = False

    def _init_ui(self) -> None:
        """Initialize the UI components"""
        # Top section for mod import
        self._init_import_section()

        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        self._layout.addWidget(separator)

        # Browse mods section
        self._init_browse_section()

        # Status bar
        self._layout.addWidget(self.online_status_bar)

    def _init_import_section(self) -> None:
        """Initialize the local mod import section"""
        import_label = QLabel("Import Local Mods")
        self._layout.addWidget(import_label)

        import_desc = QLabel("Import mod files from your computer")
        import_desc.setWordWrap(True)
        self._layout.addWidget(import_desc)

        import_button = QPushButton("Import Mod Files")
        import_button.clicked.connect(self.install_local_mod)
        self._layout.addWidget(import_button)

    def _init_browse_section(self) -> None:
        """Initialize the online mod browsing section"""
        browse_label = QLabel("Browse Online Mods")
        self._layout.addWidget(browse_label)

        # Provider selection
        provider_layout = QHBoxLayout()
        provider_label = QLabel("Select Provider:")
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(list(self.providers.keys()))
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        provider_layout.addWidget(provider_label)
        provider_layout.addWidget(self.provider_combo)

        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_table)
        provider_layout.addWidget(refresh_button)
        provider_layout.addStretch()
        self._layout.addLayout(provider_layout)

        # Mods table
        self._layout.addWidget(self.online_mods_table)

    def _init_mods_table(self) -> QTableWidget:
        """Initialize the online mods table"""
        table = QTableWidget()
        table.setSortingEnabled(True)
        table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self._show_context_menu)

        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(48)

        headers = ["", "Name", "Version", "Authors", "Rating", "Downloads", "Last Updated", ""]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)

        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setMinimumSectionSize(48)

        header.resizeSection(0, 48)
        header.resizeSection(4, 80)
        header.resizeSection(7, 150)

        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)

        header.resizeSection(1, 275)
        header.resizeSection(2, 125)
        header.resizeSection(3, 120)
        header.resizeSection(5, 120)
        header.resizeSection(6, 175)

        return table

    def _show_context_menu(self, position: QPoint) -> None:
        """Show context menu for a mod"""
        item = self.online_mods_table.itemAt(position)
        if not item:
            return

        # Get the mod info from the first column of the selected row
        row = self.online_mods_table.row(item)
        mod_item = self.online_mods_table.item(row, 0)
        if not mod_item:
            return

        global_pos = self.online_mods_table.viewport().mapToGlobal(position)
        context_menu = GetModsContextMenu(self, self.logger)
        context_menu.show_menu(global_pos, mod_item)

    async def _add_mod_to_table(self, mod: ModInfo) -> None:
        """Add a mod to the online mods table"""
        # First check if we already have the icon cached
        icon_data = None
        if mod.web_id:
            icon_data = self.db.get_mod_icon(mod.web_id)

            # If not cached, download and store it
            if not icon_data and mod.icon_url:
                icon_data = await self.current_provider.download_mod_icon(mod)
                if icon_data:
                    self.db.store_mod_icon(mod.web_id, icon_data)

        row_position = self.online_mods_table.rowCount()
        self.online_mods_table.insertRow(row_position)

        # Create item to store mod data in the first column
        mod_item = QTableWidgetItem()
        mod_item.setData(Qt.ItemDataRole.UserRole, mod)
        self.online_mods_table.setItem(row_position, 0, mod_item)

        # Create and setup icon label
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setMinimumSize(48, 48)
        icon_label.setMaximumSize(48, 48)

        # Load icon image
        if icon_data:
            pixmap = QPixmap()
            if pixmap.loadFromData(icon_data):
                scaled_pixmap = pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)
                icon_label.setPixmap(scaled_pixmap)
        else:
            # Load default icon
            default_icon_path = Path(__file__).parent.parent.parent / "assets" / "default_icon.png"
            if default_icon_path.exists():
                pixmap = QPixmap(str(default_icon_path))
                scaled_pixmap = pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)
                icon_label.setPixmap(scaled_pixmap)
            else:
                icon_label.setText("📦")  # Fallback emoji

        self.online_mods_table.setCellWidget(row_position, 0, icon_label)

        # Basic info columns
        self.online_mods_table.setItem(row_position, 1, QTableWidgetItem(mod.display_name))
        self.online_mods_table.setItem(row_position, 2, QTableWidgetItem(mod.version))
        self.online_mods_table.setItem(row_position, 3, QTableWidgetItem(mod.authors))

        # Rating column
        rating_item = QTableWidgetItem("")
        rating_item.setData(Qt.ItemDataRole.UserRole, mod.rating)
        self.online_mods_table.setItem(row_position, 4, rating_item)

        self.online_mods_table.setItem(row_position, 5, QTableWidgetItem(str(mod.download_count)))
        self.online_mods_table.setItem(row_position, 6, QTableWidgetItem(
            mod.last_updated.strftime("%Y-%m-%d %H:%M")))

        # Action column
        action_item = QTableWidgetItem("")
        self.online_mods_table.setItem(row_position, 7, action_item)

        # Store full mod info
        mod_item.setData(Qt.ItemDataRole.UserRole, mod)

        # Create widgets for rating and download button
        self.online_mods_table.setCellWidget(row_position, 4, StarRatingWidget(mod.rating))
        action_widget = ModActionWidget(mod.__dict__, self.db)
        action_widget.button.clicked.connect(
            lambda checked, m=mod: self._download_online_mod(m))
        self.online_mods_table.setCellWidget(row_position, 7, action_widget)

    @asyncSlot()
    async def _on_provider_changed(self, provider_name: str) -> None:
        """Handle provider selection change"""
        try:
            provider_class = self.providers[provider_name]
            self.current_provider = provider_class()
            await self.refresh_table()
        except KeyError:
            self.logger.error("Unknown provider: %s", provider_name)
            self.online_status_bar.showMessage("Failed to initialize provider")

    @asyncSlot()
    async def refresh_table(self) -> None:
        """Search for mods using the current provider"""
        if self.is_loading:
            return
        self.is_loading = True
        self.online_mods_table.setSortingEnabled(False)

        if not self.current_provider:
            self.online_status_bar.showMessage("No provider selected")
            return

        self.online_status_bar.showMessage("Searching for mods...")
        self.online_mods_table.clearContents()
        self.online_mods_table.setRowCount(0)
        self.current_page = 1

        try:
            while self.current_page <= self.total_pages:
                mods, total_pages = await self.current_provider.search_mods(self.current_page)
                self.total_pages = total_pages

                for mod in mods:
                    await self._add_mod_to_table(mod)
                self.current_page += 1
        except (ParserError, RuntimeError) as e:
            self.logger.error("Failed to fetch mods: %s", str(e))
            self.online_status_bar.showMessage(f"Failed to fetch mods: {str(e)}")
        finally:
            self.is_loading = False
            self.online_mods_table.setSortingEnabled(True)
            self.online_status_bar.showMessage(
                f"Found {self.online_mods_table.rowCount()} mods")

    @asyncSlot()
    async def _download_online_mod(self, mod: ModInfo) -> None:
        """Download and install a mod from online provider"""
        if not self.current_provider:
            return

        self.online_status_bar.showMessage(f"Downloading {mod.display_name}...")

        try:
            file_name = await self.current_provider.download_mod(mod, str(self.paths.temp_path))

            if file_name is None:
                raise RuntimeError("External download required")

            # Extract and install the mod
            metadata = self._install_mod_from_file(file_name)

            # Link the icon to the installed mod if we have both web_id and mod_id
            if metadata and metadata.web_id and metadata.mod_id:
                self.db.link_icon_to_mod(metadata.web_id, metadata.mod_id)

            self.online_status_bar.showMessage(
                f"Successfully installed {mod.display_name}")

        except (RuntimeError, IOError) as e:
            error_msg = f"Failed to download mod: {str(e)}"
            self.logger.error(error_msg)
            self.online_status_bar.showMessage(error_msg)
            QMessageBox.critical(self, "Download Error", error_msg, QMessageBox.StandardButton.Ok)
        finally:
            for file in os.listdir(self.paths.temp_path):
                file_path = self.paths.temp_path / file
                if file_path.is_file():
                    file_path.unlink()
                else:
                    shutil.rmtree(file_path)

    def _install_mod_from_file(self, file_name: str) -> Optional[ModInfo]:
        """Install a mod from a downloaded file

        Returns:
            The parsed mod metadata if successful, None otherwise
        """
        self.paths.ensure_all_directories()

        try:
            target_path = self.storage_path / file_name.split(".")[0]
            extracted_path = Ah.extract(self.paths.temp_path / file_name,
                                        self.paths.temp_path / file_name.split(".")[0])
            if not extracted_path.path:
                raise RuntimeError(
                    f"Failed to extract mod: {extracted_path.message}")

            mod_info = None
            for match in extracted_path.path.rglob("*.modinfo"):
                mod_info = match
                break
            if mod_info is None:
                raise RuntimeError("Failed to find modinfo file in archive")
            mod_root = mod_info.parent

            metadata = parse_modinfo(mod_info)
            if not metadata:
                raise RuntimeError(f"Failed to parse modinfo file: {mod_info}")

            if isinstance(metadata, dict):
                metadata["file_path"] = str(target_path)
            else:
                metadata.file_path = str(target_path)
            self.db.add_installed_mod(metadata)

            if target_path.exists():
                shutil.rmtree(target_path)

            shutil.move(mod_root, target_path)

            return metadata

        except (RuntimeError, IOError, ParseError) as e:
            error_msg = f"Failed to install mod: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def install_local_mod(self) -> None:
        """Install mods from local files"""
        if not self.storage_path or not self.db:
            return

        archives, _ = QFileDialog.getOpenFileNames(
            self, "Select Mod Archives", "", self.archive_filter)

        if not archives:
            return

        self.logger.info(
            "Attempting to install mod%s", "s" if len(archives) > 1 else "")
        total_mods = len(archives)
        failed_installs = 0
        skipped_installs = 0
        yes_to_all = False
        no_to_all = False

        for archive in archives:
            try:
                with tempfile.TemporaryDirectory() as temp_dir_str:
                    temp_dir = Path(temp_dir_str)
                    folder_name = Path(archive).stem
                    target_path = self.storage_path / folder_name

                    # User interaction for existing mods
                    if target_path.exists() and not yes_to_all:
                        if no_to_all:
                            skipped_installs += 1
                            continue

                        reply = QMessageBox.question(
                            self,
                            "Overwrite Mod?",
                            f"Mod '{folder_name}' already exists. Overwrite?",
                            QMessageBox.StandardButton.Yes |
                            QMessageBox.StandardButton.No |
                            QMessageBox.StandardButton.YesToAll |
                            QMessageBox.StandardButton.NoToAll,
                            QMessageBox.StandardButton.No
                        )

                        if reply == QMessageBox.StandardButton.No:
                            skipped_installs += 1
                            continue
                        elif reply == QMessageBox.StandardButton.NoToAll:
                            skipped_installs += 1
                            no_to_all = True
                            continue
                        elif reply == QMessageBox.StandardButton.YesToAll:
                            yes_to_all = True

                    # Extract and process mod
                    try:
                        extracted_path = Ah.extract(Path(archive), temp_dir)
                        if not extracted_path.path:
                            raise RuntimeError(
                                f"Failed to extract {folder_name}: {extracted_path.message}")

                        # Find modinfo file
                        mod_info = None
                        for match in extracted_path.path.rglob("*.modinfo"):
                            mod_info = match
                            break
                        if mod_info is None:
                            raise RuntimeError(f"No .modinfo file found in {folder_name}")
                        mod_root = mod_info.parent

                        # Parse mod metadata
                        metadata = parse_modinfo(mod_info)
                        if not metadata:
                            raise RuntimeError(f"Failed to parse {mod_info}")

                        if isinstance(metadata, dict):
                            metadata["file_path"] = str(target_path)
                        else:
                            metadata.file_path = str(target_path)

                        # Install mod
                        if target_path.exists():
                            shutil.rmtree(target_path)
                        shutil.move(mod_root, target_path)
                        self.db.add_installed_mod(metadata)

                    except (RuntimeError, IOError, ParseError) as e:
                        self.logger.error("Failed to process mod %s: %s", folder_name, e)
                        failed_installs += 1
                        continue

            except (OSError, shutil.Error) as e:
                self.logger.error("Failed to handle mod file %s: %s", archive, e)
                failed_installs += 1

        msg = (
            f"Installation complete: {total_mods-failed_installs-skipped_installs} successful, "
            f"{failed_installs} failed, {skipped_installs} skipped"
        )
        self.logger.info(msg)
        QMessageBox.information(self, "Installation Complete", msg, QMessageBox.StandardButton.Ok)


class GetModsContextMenu:
    """Handler for get mods page context menu operations"""

    def __init__(self, parent: QWidget, logger):
        self.parent = parent
        self.logger = logger

    def show_menu(self, position: QPoint, item: QTableWidgetItem) -> None:
        """Show the context menu for an online mod item"""
        menu = QMenu()
        open_url_action = menu.addAction("Open in Browser")

        action = menu.exec(position)
        if not action:
            return

        mod_data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(mod_data, ModInfo):
            return

        if action == open_url_action:
            self._open_mod_url(mod_data)

    def _open_mod_url(self, mod_info: ModInfo) -> None:
        """Open the mod's URL in the default browser"""
        if not mod_info.web_id:
            QMessageBox.warning(self.parent, "Error", "No URL available for this mod")
            return

        url = f"https://forums.civfanatics.com/resources/{mod_info.web_id}"
        QDesktopServices.openUrl(QUrl(url))
