"""Configuration and path management for the Civilization VII Mod Manager"""
import os
import tempfile
from pathlib import Path


class ModManagerPaths:
    """Handles path management for the mod manager"""

    def __init__(self):
        local_appdata = os.getenv("LOCALAPPDATA")
        if local_appdata is None:
            raise EnvironmentError("Unable to locate LOCALAPPDATA environment variable")
        self._local_appdata = str(local_appdata)

        self._app_path: Path = Path(__file__).parent
        self._game_mods_path: Path = \
            Path(self._local_appdata) / "Firaxis Games" / "Sid Meier's Civilization VII" / "Mods"
        self._storage_path: Path = Path(self._local_appdata) / "Civ7ModManager" / "ModStorage"
        self._profiles_path: Path = Path(self._local_appdata) / "Civ7ModManager" / "Profiles"
        self._logs_path: Path = Path(self._local_appdata) / "Civ7ModManager" / "Logs"
        self._db_path: Path = Path(self._local_appdata) / "Civ7ModManager" / "mods.db"
        
        self._temp_dir = tempfile.TemporaryDirectory(prefix="Civ7ModManager_")
        self._temp_path: Path = Path(self._temp_dir.name)

        self.ensure_all_directories()

    #region Property getters and setters
    @property
    def app_path(self) -> Path:
        """Get the application path"""
        return self._app_path

    @property
    def game_mods_path(self) -> Path:
        """Get the game mods directory path"""
        return self._game_mods_path

    @game_mods_path.setter
    def game_mods_path(self, path: Path | str) -> None:
        """Set the game mods directory path"""
        self._game_mods_path = Path(path)
        self.ensure_directory(self._game_mods_path)

    @property
    def storage_path(self) -> Path:
        """Get the mod storage path"""
        return self._storage_path

    @storage_path.setter
    def storage_path(self, path: Path | str) -> None:
        """Set the mod storage path"""
        self._storage_path = Path(path)
        self.ensure_directory(self._storage_path)

    @property
    def profiles_path(self) -> Path:
        """Get the profiles directory path"""
        return self._profiles_path

    @profiles_path.setter
    def profiles_path(self, path: Path | str) -> None:
        """Set the profiles directory path"""
        self._profiles_path = Path(path)
        self.ensure_directory(self._profiles_path)

    @property
    def logs_path(self) -> Path:
        """Get the logs directory path"""
        return self._logs_path

    @logs_path.setter
    def logs_path(self, path: Path | str) -> None:
        """Set the logs directory path"""
        self._logs_path = Path(path)
        self.ensure_directory(self._logs_path)

    @property
    def temp_path(self) -> Path:
        """Get the temporary directory path"""
        return self._temp_path

    @temp_path.setter
    def temp_path(self, path: Path | str) -> None:
        """Set the temporary directory path. Note: This will not move existing temp files."""
        if self._temp_dir is not None:
            self._temp_dir.cleanup()
        # Create new temporary directory at specified location
        self._temp_dir = tempfile.TemporaryDirectory(dir=str(path))
        self._temp_path = Path(self._temp_dir.name)

    @property
    def db_path(self) -> Path:
        """Get the database file path"""
        return self._db_path

    @db_path.setter
    def db_path(self, path: Path | str) -> None:
        """Set the database file path"""
        self._db_path = Path(path)
        self.ensure_directory(self._db_path.parent)
    #endregion

    def ensure_directory(self, path: Path) -> None:
        """Ensure a directory exists, creating it if necessary

        Args:
            path: The directory path to ensure exists
        """
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise OSError(f"Failed to create directory {path}: {str(e)}") from e

    def ensure_all_directories(self) -> None:
        """Ensure all required directories exist"""
        for path in [
            self.game_mods_path,
            self.storage_path,
            self.profiles_path,
            self.logs_path,
            self.temp_path,
            self.db_path.parent
        ]:
            self.ensure_directory(path)

    def reset_to_defaults(self) -> None:
        """Reset all paths to their default values and ensure directories exist"""
        # Re-initialize paths with default values
        self._game_mods_path = Path(self._local_appdata) / "Firaxis Games" / "Sid Meier's Civilization VII" / "Mods"
        self._storage_path = Path(self._local_appdata) / "Civ7ModManager" / "ModStorage"
        self._profiles_path = Path(self._local_appdata) / "Civ7ModManager" / "Profiles"
        self._logs_path = Path(self._local_appdata) / "Civ7ModManager" / "Logs"
        if self._temp_dir is not None:
            self._temp_dir.cleanup()
        self._temp_dir = tempfile.TemporaryDirectory(prefix="Civ7ModManager_")
        self._temp_path = Path(self._temp_dir.name)
        self._db_path = Path(self._local_appdata) / "Civ7ModManager" / "mods.db"
        self.ensure_all_directories()
