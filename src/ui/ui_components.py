from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QTableWidgetItem, QWidget, QHBoxLayout,
    QPushButton, QLabel
)
from PySide6.QtGui import QPixmap

from utilities.database import ModDatabase
from utilities.constants import DEFAULT_ICON_SIZE


class ModTableItem(QTableWidgetItem):
    """Custom QTableWidgetItem for displaying mod information in a table"""

    def __init__(self, mod_id: str, db: ModDatabase):
        super().__init__()
        self.db = db
        self.mod_id = mod_id
        self.update_display()

    def update_display(self):
        """Update the item's display text"""
        mod_info = self.db.get_installed_mod(self.mod_id)
        if mod_info is None:
            return

        self.setCheckState(Qt.CheckState.Checked if mod_info.get('enabled', False) else Qt.CheckState.Unchecked)

        table = self.tableWidget()
        if not table:
            return

        row = table.row(self)

        # Create icon label in second column
        icon_label = table.cellWidget(row, 0)
        if not isinstance(icon_label, QLabel):
            icon_label = QLabel()
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setMinimumSize(DEFAULT_ICON_SIZE, DEFAULT_ICON_SIZE)
            icon_label.setMaximumSize(DEFAULT_ICON_SIZE, DEFAULT_ICON_SIZE)
            table.setCellWidget(row, 0, icon_label)

        # Load icon image
        web_id = mod_info.get('web_id')
        if web_id:
            icon_data = self.db.get_mod_icon(web_id)
            if icon_data:
                pixmap = QPixmap()
                if pixmap.loadFromData(icon_data):
                    scaled_pixmap = pixmap.scaled(DEFAULT_ICON_SIZE, DEFAULT_ICON_SIZE,
                                                  Qt.AspectRatioMode.KeepAspectRatio,
                                                  Qt.TransformationMode.SmoothTransformation)
                    icon_label.setPixmap(scaled_pixmap)
                    return

        # Load default icon if no custom icon
        default_icon_path = Path(__file__).parent.parent.parent / "assets" / "default_icon.png"
        if default_icon_path.exists():
            pixmap = QPixmap(str(default_icon_path))
            scaled_pixmap = pixmap.scaled(DEFAULT_ICON_SIZE, DEFAULT_ICON_SIZE,
                                          Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)
            icon_label.setPixmap(scaled_pixmap)
        else:
            icon_label.setText("📦")  # Fallback emoji

        # Set data for other columns
        if table:
            # Display Name column
            display_name_item = QTableWidgetItem(mod_info.get('display_name', ''))
            table.setItem(row, 1, display_name_item)
            # Version column
            version_item = QTableWidgetItem(mod_info.get('version', ''))
            table.setItem(row, 2, version_item)
            # Authors column
            authors_item = QTableWidgetItem(mod_info.get('authors', ''))
            table.setItem(row, 3, authors_item)
            # Affects Saves column
            affects_saves = bool(mod_info.get('affects_saves'))
            affects_saves_text = 'Yes' if affects_saves else 'No' if affects_saves is not None else ''
            affects_saves_item = QTableWidgetItem(affects_saves_text)
            table.setItem(row, 4, affects_saves_item)
            # Has Conflicts column - to be implemented
            conflicts_item = QTableWidgetItem('')
            table.setItem(row, 5, conflicts_item)


class StarRatingWidget(QWidget):
    """Custom widget for displaying a star rating"""
    def __init__(self, rating: float):
        super().__init__(None)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)

        # Create star labels
        full_stars = int(rating)
        has_half_star = (rating - full_stars) >= 0.5

        for i in range(5):
            star = QLabel()
            if i < full_stars:
                star.setText("★")  # Full star
            elif i == full_stars and has_half_star:
                star.setText("⯨")  # Half star
            else:
                star.setText("☆")  # Empty star
            star.setStyleSheet("color: gold;")
            layout.addWidget(star)

        layout.addStretch()


class ModActionWidget(QWidget):
    """Widget for mod action buttons (Download/Update/Install)"""
    def __init__(self, mod_info: dict, db: ModDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self.mod_info = mod_info
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.button = QPushButton()
        self.button.setFixedHeight(40)
        self.button.setFixedWidth(140)
        layout.addWidget(self.button)
        
        self.update_button_state()

    def update_button_state(self):
        """Update button text and state based on mod status"""
        web_id = self.mod_info.get('web_id')
        if not web_id:
            self.button.setText("Invalid Mod")
            self.button.setEnabled(False)
            return

        # Check if mod is installed
        installed_mods = self.db.get_all_installed_mods()
        installed_mod = next((m for m in installed_mods if m.get('web_id') == web_id), None)
        
        if not installed_mod:
            self.button.setText("Download")
            self.button.setEnabled(True)
            return

        # Compare versions to check for updates
        installed_version = installed_mod.get('version', '0')
        new_version = self.mod_info.get('version', '0')
        
        if installed_version != new_version:
            self.button.setText("Update")
            self.button.setEnabled(True)
        else:
            self.button.setText("Installed")
            self.button.setEnabled(False)
