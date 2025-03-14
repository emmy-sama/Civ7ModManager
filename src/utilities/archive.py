import subprocess
import sys
import os
from pathlib import Path
from typing import NamedTuple
from zipfile import ZipFile
from py7zr import SevenZipFile

class ArchiveError(Exception):
    """Base exception for archive operations"""
    pass

class ArchiveResult(NamedTuple):
    """Result of an archive extraction operation"""
    message: str
    path: Path | None = None

def extract_zip(file_path: Path, extract_path: Path) -> ArchiveResult:
    """Extract a ZIP archive to the specified path"""
    with ZipFile(file_path, 'r') as archive:
        archive.extractall(extract_path)
    return ArchiveResult(message=f"Successfully extracted {file_path} to {extract_path}", path=extract_path)

def extract_7z(file_path: Path, extract_path: Path) -> ArchiveResult:
    """Extract a 7Z archive to the specified path"""
    with SevenZipFile(file_path, 'r') as archive:
        archive.extractall(extract_path)
    return ArchiveResult(message=f"Successfully extracted {file_path} to {extract_path}", path=extract_path)

def extract_rar(file_path: Path, extract_path: Path) -> ArchiveResult:
    """Extract a RAR archive to the specified path"""
    base_path = getattr(sys, '_MEIPASS', Path(__file__).parent.parent)
    unrar_path = base_path.parent / "lib" / "UnRAR.exe"
    
    if not unrar_path.exists():
        raise FileNotFoundError(f"UnRAR executable missing from: {unrar_path}")
    if not os.access(unrar_path, os.X_OK):
        raise ArchiveError(f"UnRAR executable does not have execute permissions")
    
    try:
        subprocess.run(
            [str(unrar_path), "x", str(file_path), str(extract_path) + "\\", "-r", "-y"],
            check=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
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
            error_msg = "Unrar error: " + error_messages.get(e.returncode, f"Failed with code {e.returncode}")
            raise ArchiveError(error_msg)
    
    return ArchiveResult(message=f"Successfully extracted {file_path} to {extract_path}", path=extract_path)

def unsuported_file(file_path: Path, *args) -> ArchiveResult:
    return ArchiveResult(message=f"Unsupported archive format: {file_path.suffix}")

extractors = {
            '.zip': extract_zip,
            '.7z': extract_7z,
            '.rar': extract_rar,
            '.r00': extract_rar
        }

def extract(file_path: Path, target_path: Path|None = None) -> ArchiveResult:
    """Extract an archive to a target directory or inplace if target is None"""
    if target_path is None:
        target_path = file_path.parent
    if not file_path.exists():
        return ArchiveResult(message=f"Archive not found: {file_path}")
    os.mkdir(target_path)
    if not target_path.exists():
        return ArchiveResult(message=f"Target directory not found: {target_path}")
    
    result = extractors.get(file_path.suffix, unsuported_file)(file_path, target_path)
    
    return result