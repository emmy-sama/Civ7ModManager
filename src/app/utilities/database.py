"""Database module for managing installed mods"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, NamedTuple

from .modinfo_parser import ModInfo


class ModCount(NamedTuple):
    total: int
    enabled: int


class ModDatabase:
    """Class for managing the mod database"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create installed_mods table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS installed_mods (
                    enabled BOOLEAN DEFAULT FALSE,
                    mod_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    affects_saves BOOLEAN,
                    version TEXT,
                    authors TEXT,
                    tag_line TEXT,
                    web_id TEXT,
                    description TEXT,
                    download_count INTEGER DEFAULT 0,
                    update_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    raiting REAL DEFAULT 0.0,
                    icon_url TEXT
                )
            ''')

            # Create mod_dependencies table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mod_dependencies (
                    mod_id TEXT,
                    dependency_id TEXT,
                    FOREIGN KEY(mod_id) REFERENCES installed_mods(mod_id),
                    PRIMARY KEY(mod_id, dependency_id)
                )
            ''')

            # Create affected_files table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS affected_files (
                    mod_id TEXT,
                    file_name TEXT,
                    action TEXT,
                    FOREIGN KEY(mod_id) REFERENCES installed_mods(mod_id),
                    PRIMARY KEY(mod_id, file_name, action)
                )
            ''')

            # Create mod_icons table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mod_icons (
                    web_id TEXT PRIMARY KEY,
                    mod_id TEXT,
                    icon_data BLOB NOT NULL,
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(mod_id) REFERENCES installed_mods(mod_id)
                )
            ''')

    def add_installed_mod(self, mod_info: ModInfo) -> None:
        """Add a mod to the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT or REPLACE into installed_mods (
                    mod_id, display_name, file_path, provider, affects_saves,
                    version, authors, tag_line, web_id, description, download_count,
                    update_date, raiting, icon_url
                ) VALUES (?,?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                mod_info.mod_id, mod_info.display_name, mod_info.file_path, mod_info.provider,
                mod_info.affects_saves, mod_info.version, mod_info.authors, mod_info.tag_line,
                mod_info.web_id, mod_info.description, mod_info.download_count,
                mod_info.last_updated, mod_info.rating, mod_info.icon_url
            ))

    def remove_installed_mod(self, mod_id: str) -> None:
        """Remove a mod and its related data from the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM affected_files WHERE mod_id = ?', (mod_id,))
            cursor.execute('DELETE FROM mod_dependencies WHERE mod_id = ?', (mod_id,))
            cursor.execute('DELETE FROM installed_mods WHERE mod_id = ?', (mod_id,))

    def get_installed_mod(self, mod_id: str, cols: str = '*', dependencies: bool = True,
                          affected_files: bool = True) -> Optional[Dict]:
        """Get information about an installed mod"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get basic mod info
            cursor.execute(f'SELECT {cols} FROM installed_mods WHERE mod_id = ?', (mod_id,))
            columns = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
            if not row:
                return None

            # Convert row to dict with column names
            mod_info = dict(zip(columns, row))
            if 'affects_saves' in mod_info:
                mod_info['affects_saves'] = bool(mod_info['affects_saves'])
            if 'enabled' in mod_info:
                mod_info['enabled'] = bool(mod_info['enabled'])

            # Get dependencies
            if dependencies:
                cursor.execute('SELECT dependency_id FROM mod_dependencies WHERE mod_id = ?', (mod_id,))
                mod_info['dependencies'] = [{'id': row[0]} for row in cursor.fetchall()]

            # Get affected files
            if affected_files:
                cursor.execute('SELECT file_name, action FROM affected_files WHERE mod_id = ?', (mod_id,))
                mod_info['affected_files'] = {row[0] for row in cursor.fetchall()}

            return mod_info

    def get_all_installed_mods(self, cols: str = '*', dependencies: bool = True, affected_files: bool = True) -> List[Dict]:
        """Get information about all installed mods"""
        mods = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT mod_id FROM installed_mods')
            for (mod_id,) in cursor.fetchall():
                mod_info = self.get_installed_mod(mod_id, cols, dependencies, affected_files)
                if mod_info:
                    mods.append(mod_info)
        return mods

    def get_all_enabled_mods(self, cols: str = '*', dependencies: bool = True, affected_files: bool = True) -> List[Dict]:
        """Get information about all enabled mods"""
        mods = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT mod_id FROM installed_mods WHERE enabled = TRUE')
            for (mod_id,) in cursor.fetchall():
                mod_info = self.get_installed_mod(mod_id, cols, dependencies, affected_files)
                if mod_info:
                    mods.append(mod_info)
        return mods

    def update_mod_enabled_state(self, mod_id: str, enabled: bool) -> None:
        """Update the enabled state of a mod"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE installed_mods
                SET enabled = ?
                WHERE mod_id = ?
            ''', (enabled, mod_id))

    def set_mod_enabled(self, mod_id: str, enabled: bool) -> None:
        """Set the enabled state of a mod"""
        self.update_mod_enabled_state(mod_id, enabled)

    def get_mod_path(self, mod_id: str) -> Optional[Path]:
        """Get the file path for a mod"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT file_path FROM installed_mods WHERE mod_id = ?', (mod_id,))
            row = cursor.fetchone()
            if row and row[0] != '':
                return Path(row[0])
            return None

    def enable_all_mods(self) -> None:
        """Enable all installed mods"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE installed_mods SET enabled = TRUE')

    def disable_all_mods(self) -> None:
        """Disable all installed mods"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE installed_mods SET enabled = FALSE')

    def count_mods(self) -> ModCount:
        """Get the number of installed and enabled mods"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM installed_mods')
            total = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM installed_mods WHERE enabled = TRUE')
            enabled = cursor.fetchone()[0]
            return ModCount(total, enabled)

    def store_mod_icon(self, web_id: str, icon_data: bytes, mod_id: str | None = None) -> None:
        """Store a mod's icon in the database
        
        Args:
            web_id: The web ID of the mod
            icon_data: The binary image data
            mod_id: Optional mod ID if the mod is installed
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO mod_icons (web_id, mod_id, icon_data, last_updated)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (web_id, mod_id, icon_data))

    def get_mod_icon(self, web_id: str) -> Optional[bytes]:
        """Get a mod's icon from the database
        
        Args:
            web_id: The web ID of the mod
            
        Returns:
            The icon binary data if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT icon_data FROM mod_icons WHERE web_id = ?', (web_id,))
            row = cursor.fetchone()
            return row[0] if row else None

    def link_icon_to_mod(self, web_id: str, mod_id: str) -> None:
        """Link an existing icon to an installed mod
        
        Args:
            web_id: The web ID of the mod 
            mod_id: The installed mod ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE mod_icons 
                SET mod_id = ?, last_updated = CURRENT_TIMESTAMP
                WHERE web_id = ?
            ''', (mod_id, web_id))

    def remove_mod_icon(self, web_id: str) -> None:
        """Remove a mod's icon from the database
        
        Args:
            web_id: The web ID of the mod
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM mod_icons WHERE web_id = ?', (web_id,))
