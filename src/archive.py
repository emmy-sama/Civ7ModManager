import shutil
import subprocess
from pathlib import Path
from typing import Literal

from zipfile import ZipFile
from py7zr import SevenZipFile

class ArchiveError(Exception):
    """Base exception for archive operations"""
    pass

class ArchiveHandler:
    """Handles different types of archive files using native Python libraries and command-line tools"""
    
    @staticmethod
    def _get_archive_type(file_path) -> Literal['zip'] | Literal['7z'] | Literal['rar']:
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
    def extract_mod_folder(cls, file_path_str: str, target_path_str: str) -> tuple[int, str]:
        """Extract the archive and move/rename the mod folder appropriately"""
        
        archive_type = cls._get_archive_type(file_path_str)
        file_path = Path(file_path_str)
        target_path = Path(target_path_str)
        
        try:
            # Create a temporary extraction directory with a unique name
            temp_extract = target_path / f"_temp_{Path(file_path).stem}"
            temp_extract.mkdir(exist_ok=True)
            
            # Extract everything to temp directory first
            match archive_type:
                case 'zip':
                    with ZipFile(file_path, 'r') as archive:
                        archive.extractall(temp_extract)
                case '7z':
                    with SevenZipFile(file_path, 'r') as archive:
                        archive.extractall(temp_extract)
                case 'rar':
                    try:
                        app_path = Path(__file__).parent.parent
                        unrar_path = app_path / "lib" / "UnRAR.exe"
                        
                        if not unrar_path.exists():
                            raise ArchiveError(f"UnRAR executable not found at {unrar_path}")
                        subprocess.run(
                            [str(unrar_path), "x", str(file_path), str(temp_extract) + "\\", "-r", "-y"],
                            check=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
                        )
                    except subprocess.CalledProcessError as e:
                        if e.returncode != 1:  # Ignore warning code 1
                            raise
                        
            # Search for .modinfo file in the extracted contents
            modinfo_files = list(temp_extract.rglob("*.modinfo"))
            
            if not modinfo_files:
                raise ArchiveError("No .modinfo file found in archive.")
                
            # Get the first .modinfo file found
            modinfo_path = modinfo_files[0]
            mod_name = modinfo_path.stem
            
            # Determine if we need to move files or just rename the temp folder
            target_mod_path = target_path / mod_name
            mod_root = modinfo_path.parent
            
            # TODO: Prompt user to overwrite instead of just assuming it's okay
            if target_mod_path.exists():
                    shutil.rmtree(target_mod_path)
            
            if mod_root == temp_extract: # .modinfo is at root of temp folder, just rename temp folder
                temp_extract.rename(target_mod_path)
            else: # .modinfo is in a subfolder, move that folder to target
                shutil.move(str(mod_root), str(target_mod_path))
                # Clean up temp directory since we moved the contents
                shutil.rmtree(temp_extract)
            
            return 1, f"Successfully installed {mod_name}"
        
        except subprocess.CalledProcessError as e:
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
            error_msg = "Unrar: " + error_messages.get(e.returncode, f"Failed with code {e.returncode}")
            
            raise ArchiveError(error_msg)
        
        except Exception as e:
            # Clean up temp directory on error and return error status
            for file in target_path.rglob("_temp_*"):
                if file.is_dir():
                    shutil.rmtree(file)
            return 0, str(e)