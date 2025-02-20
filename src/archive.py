import subprocess
from pathlib import Path
import zipfile
import py7zr
import shutil
import re

class ArchiveError(Exception):
    """Base exception for archive operations"""
    pass

class ArchiveHandler:
    """Handles different types of archive files using native Python libraries and command-line tools"""
    
    @staticmethod
    def is_format_supported(archive_type):
        """Check if a specific archive format is supported"""
        if archive_type == 'zip':
            return True  # zip support is built into Python
        elif archive_type == '7z':
            try:
                import py7zr
                return True
            except ImportError:
                return False
        elif archive_type in ['rar', 'r00']:
            app_path = Path(__file__).parent.parent
            unrar_path = app_path / "lib" / "UnRAR.exe"
            return unrar_path.exists()
        return False

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

    @classmethod
    def extract_mod_folder(cls, file_path, target_path, mod_folder=None):
        """Extract the archive and move/rename the mod folder appropriately"""
        archive_type = cls.get_archive_type(file_path)
        file_path = Path(file_path)
        target_path = Path(target_path)
        
        # Create a temporary extraction directory with a unique name
        temp_extract = target_path / f"_temp_{Path(file_path).stem}"
        temp_extract.mkdir(exist_ok=True)
        
        try:
            # Extract everything to temp directory first
            if archive_type == 'zip':
                with zipfile.ZipFile(file_path, 'r') as archive:
                    archive.extractall(temp_extract)
                    
            elif archive_type == 'rar':
                try:
                    app_path = Path(__file__).parent.parent
                    unrar_path = app_path / "lib" / "UnRAR.exe"
                    
                    if not unrar_path.exists():
                        raise ArchiveError(f"UnRAR executable not found at {unrar_path}")
                    
                    try:
                        result = subprocess.run(
                            [str(unrar_path), "x", str(file_path), str(temp_extract) + "\\", "-r", "-y"],
                            check=True,
                            capture_output=True,
                            text=True,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                    except subprocess.CalledProcessError as e:
                        if e.returncode != 1:  # Ignore warning code 1
                            error_messages = {
                                2: "Fatal error in archive",
                                3: "Invalid archive or CRC error",
                                4: "Archive is locked or encrypted",
                                5: "Write error occurred",
                                6: "File open error",
                                7: "Wrong command line option",
                                8: "Not enough memory",
                                9: "File create error",
                                10: "No files to extract"
                            }
                            error_msg = error_messages.get(e.returncode, f"UnRAR failed with code {e.returncode}")
                            raise ArchiveError(f"{error_msg}: {e.stderr}")
                    
                except OSError as e:
                    raise ArchiveError(f"Failed to execute UnRAR: {e}")
                    
            elif archive_type == '7z':
                with py7zr.SevenZipFile(file_path, 'r') as archive:
                    archive.extractall(temp_extract)

            # Search for .modinfo file in the extracted contents
            modinfo_files = list(temp_extract.rglob("*.modinfo"))
            
            if not modinfo_files:
                raise ArchiveError("No .modinfo file found in archive. The file does not appear to be a valid Civilization mod.")
                
            # Get the first .modinfo file found
            modinfo_path = modinfo_files[0]
            mod_name = modinfo_path.stem
            
            # Determine if we need to move files or just rename the temp folder
            if modinfo_path.parent == temp_extract:
                # .modinfo is at root of temp folder, just rename temp folder
                target_mod_path = target_path / mod_name
                if target_mod_path.exists():
                    shutil.rmtree(target_mod_path)
                temp_extract.rename(target_mod_path)
            else:
                # .modinfo is in a subfolder, move that folder to target
                mod_root = modinfo_path.parent
                while mod_root.parent != temp_extract and mod_root.parent != temp_extract.parent:
                    mod_root = mod_root.parent
                
                target_mod_path = target_path / mod_name
                if target_mod_path.exists():
                    shutil.rmtree(target_mod_path)
                shutil.move(str(mod_root), str(target_mod_path))
                
                # Clean up temp directory since we moved the contents
                shutil.rmtree(temp_extract)
            
            return mod_name
                
        except Exception as e:
            # Clean up temp directory on error
            if temp_extract.exists():
                shutil.rmtree(temp_extract)
            raise e