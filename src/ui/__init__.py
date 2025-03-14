"""Base classes for UI components"""
import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout

class BasePage(QWidget):
    """Base class for all pages in the mod manager"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger("Civ7ModManager")
        self._layout = QVBoxLayout(self)

    def refresh(self):
        """Refresh the page content. Should be implemented by subclasses."""