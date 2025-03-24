"""Main application class for Civ7 Mod Manager."""
import sys
import asyncio

from typing import Sequence

from qasync import QEventLoop
from PySide6.QtWidgets import QApplication

from .ui.main_window import Civ7ModManager


class Civ7ModManagerApp(QApplication):
    """Main application class for Civ7 Mod Manager."""
    def __init__(self, arguments: Sequence[str], *args, **kwargs):
        super().__init__(arguments, *args, **kwargs)

        self.main_window = Civ7ModManager()
        self.loop = QEventLoop(self)
        asyncio.set_event_loop(self.loop)

    def run(self):
        """Run the application event loop."""
        self.main_window.show()

        with self.loop:
            sys.exit(self.loop.run_forever())
