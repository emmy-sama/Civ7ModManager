"""Module for parsing Civilization VII mod info files.

This module provides functionality to parse modinfo.xml files from Civilization VII mods
and extract relevant metadata such as mod ID, name, version, dependencies, and affected files.
"""
import logging

from typing import Literal, Optional
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from dataclasses import field
from bs4 import BeautifulSoup, Tag

from .constants import BASE_GAME_MODS, DLC_MODS

FILEACTION = Literal["update_db", "update_text", "ui_scripts", "import_files"]
PROVIDERS = Literal["local", "civfanatics"]

class ParseError(Exception):
    """Exception raised when there is an error parsing a modinfo file"""

@dataclass
class ModInfo:
    """Data class for mod information from providers"""
    # .modinfo fields
    mod_id: str
    display_name: str
    file_path: str
    provider: PROVIDERS
    affects_saves: bool | None
    version: str = "N/A"
    authors: str = "N/A"
    tag_line: str = "N/A"
    dependencies: set[str] = field(default_factory=set)
    affected_files: dict[FILEACTION, set[str]] = field(default_factory=dict)
    # Web Fetched fields
    web_id: str = ""
    description: str = ""
    download_count: int = 0
    last_updated: datetime = datetime(1970, 1, 1)
    rating: float = 0.0  # Rating out of 5 stars
    icon_url: str = ""

def parse_modinfo(modinfo_path: Path) -> Optional[ModInfo]:
    """Parse a modinfo file and return a dictionary of metadata"""
    try:
        if not modinfo_path.exists():
            raise FileNotFoundError(f"File not found: {modinfo_path}")
        with open(modinfo_path, "r", encoding="utf-8") as modinfo_file:
            modinfo_soup = BeautifulSoup(modinfo_file, "xml")

        root = modinfo_soup.select_one("Mod")
        if root is None:
            raise ParseError("No Mod element found")

        # Get basic mod info
        mod_id = root.get("id")
        if not isinstance(mod_id, str):
            raise ParseError("Mod ID not found")

        version = root.get("version")
        if not isinstance(version, str):
            version = "N/A"

        # Get properties
        properties = root.select_one("Properties")
        if properties is None:
            raise ParseError("No Properties element found")

        # Display name
        name_elm = properties.select_one("Name")
        if name_elm is None:
            raise ParseError("No Name element found")
        name: str = name_elm.text.strip()

        # If the name element starts with LOC_ try to get localized name
        if name.startswith("LOC_"):
            localization_files = root.select_one("LocalizedText")
            if localization_files:
                for loc_file in localization_files.select("File"):
                    if "en_us" in loc_file.text.strip():
                        localized_name = _get_localized_name(
                            name_elm, modinfo_path.parent / loc_file.text.strip()
                            )
                        if localized_name:
                            name = localized_name
        if name.startswith("LOC_"):
            name = mod_id

        # Authors
        authors_elm = properties.select_one("Authors")
        if authors_elm is None:
            authors = "N/A"
        else:
            authors = authors_elm.text.strip()

        # Description
        tag_line_elm = properties.select_one("Description")
        if tag_line_elm is None:
            tag_line = ""
        else:
            tag_line: str = tag_line_elm.text.strip()

        # Affects saves
        affects_saves_elm = properties.select_one("AffectsSavedGames")
        if affects_saves_elm is None:
            affects_saves = None
        else:
            affects_saves = not affects_saves_elm.text.strip() == "0"

        # Get dependencies
        dependencies = set()
        dependencies_elm = properties.select_one("Dependencies")
        if dependencies_elm:
            for dep in dependencies_elm.select("Mod"):
                dep_id = dep.get("id")
                if dep_id and dep_id not in BASE_GAME_MODS and dep_id not in DLC_MODS:
                    dependencies.add(dep_id)

        # Get affected files from all action groups
        affected_files = {
            "update_db": set(),
            "update_text": set(),
            "ui_scripts": set(),
            "import_files": set(),
        }
        for action_group in root.select("ActionGroup"):
            actions = action_group.select_one("Actions")
            if actions is not None:
                # Process UpdateDatabase actions
                update_db = affected_files.get("update_db")
                if update_db is not None:
                    for action in actions.select("UpdateDatabase"):
                        for item in action.select("Item"):
                            if item.text:
                                update_db.add(
                                    item.text.strip()
                                )

                # Process UpdateText actions
                update_text = affected_files.get("update_text")
                if update_text is not None:
                    for action in actions.select("UpdateText"):
                        for item in action.select("Item"):
                            if item.text:
                                update_text.add(
                                    item.text.strip()
                                )

                # Process UIScripts actions
                ui_scripts = affected_files.get("ui_scripts")
                if ui_scripts is not None:
                    for action in actions.select("UIScripts"):
                        for item in action.select("Item"):
                            if item.text:
                                ui_scripts.add(
                                    item.text.strip()
                                )

                # Process ImportFiles actions
                import_files = affected_files.get("import_files")
                if import_files is not None:
                    for action in actions.select("ImportFiles"):
                        for item in action.select("Item"):
                            if item.text:
                                import_files.add(
                                    item.text.strip()
                                )
        return ModInfo(
            mod_id=mod_id,
            display_name=name,
            file_path=str(modinfo_path.parent),
            provider="local",
            affects_saves=affects_saves,
            version=version,
            authors=authors,
            tag_line=tag_line,
            dependencies=dependencies,
            affected_files=affected_files,
        )

    except ParseError as e:
        logging.error("Error parsing %s: %s", modinfo_path, e)
        return None

    except FileNotFoundError:
        logging.error("File not found: %s", modinfo_path)
        return None

def _get_localized_name(name_tag: Tag, loc_file_path: Path) -> str | None:
    """Load localized name from the mod's localization file"""
    try:
        with open(loc_file_path, "r", encoding="utf-8") as loc_file:
            loc_soup = BeautifulSoup(loc_file, "xml")

        root = loc_soup.select_one("Database")
        if root is None:
            return None
        english_text = root.select_one("EnglishText")
        if english_text is None:
            return None
        # Look for the name in the localization file
        for row in english_text.select("Row"):
            tag = row.get("Tag")
            if tag and tag == name_tag:
                text = row.select_one("Text")
                if text is None:
                    return None
                return text.text.strip()
        return None

    except FileNotFoundError:
        print(f"Localization file not found for {name_tag}")
        return None
