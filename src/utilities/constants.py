"""Constants for the Civilization VII Mod Manager"""
from PySide6.QtGui import QFont


# Application version
APP_VERSION = "0.1.2"

# URLs
GITHUB_URL = "https://github.com/emmy-sama/Civ7ModManager"
CIVFANATICS_MOD_URL = "https://forums.civfanatics.com/resources/mod-manager.31957/"
CIVFANATICS_BASE_URL = "https://forums.civfanatics.com/resources/"
CIVFANATICS_CIV7_URL = "categories/civilization-vii-downloads.181/"

# Default Game Mods (not shown as dependencies)
BASE_GAME_MODS = frozenset([
    "age-antiquity",
    "age-exploration",
    "age-modern",
    "base-standard",
    "core",
    "telemetry",
])

DLC_MODS = frozenset([
    "ashoka-himiko-alt",
    "ashoka-himiko-alt-shell",
    "boot-shell",
    "friedrich-xerxes-alt",
    "friedrich-xerxes-alt-shell",
    "napoleon",
    "napoleon-alt",
    "napoleon-alt-shell",
    "napoleon-shell",
    "shawnee-tecumseh",
    "shawnee-tecumseh-shell",
])

# UI Constants
DEFAULT_WINDOW_SIZE = (1200, 800)
DEFAULT_NAV_WIDTH = 150
DEFAULT_BUTTON_HEIGHT = 40
DEFAULT_ICON_SIZE = 48


# Fonts
MAINFONT = QFont("Roboto", 16)