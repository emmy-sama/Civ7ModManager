# Civilization VII Mod Manager

A desktop application for managing, installing, and deploying mods for Civilization VII.

## Features

- Install mods from various archive formats (ZIP, RAR, 7Z)
- Batch installation of multiple mods from a folder
- Enable/disable mods with a simple checkbox interface
- View detailed mod information including dependencies and affected files
- Save and load mod profiles
- One-click deployment of enabled mods to the game directory
- Sort mods by name, ID, version, and other attributes
- Check for mod conflicts based on if they try to overwrite the same files

## Installation

### Option 1: Download Pre-built Release
Download the latest release from the [Releases](https://github.com/emmy-sama/Civ7ModManager/releases) page on GitHub.

### Option 2: Build from Source
1. Ensure you have Python 3.13 or higher installed on your system
2. Install the required dependencies:
```bash
pip install -r requirements.txt
```
3. Run pyinstaller to build
```bash
pyinstaller src\civ7modmanager.spec -y
```

## Usage

1. Launch the application by running:
```bash
python src/main.py
```

2. The application will automatically create necessary directories:
   - Mod Storage: `%LOCALAPPDATA%\Civ7ModManager\ModStorage`
   - Profiles: `%LOCALAPPDATA%\Civ7ModManager\Profiles`
   - Logs: `%LOCALAPPPAD%\Civ7ModManager\Logs`

3. Use the interface to:
   - Install new mods using the "Install Mod" or "Install Folder" buttons
   - Enable/disable mods using checkboxes
   - View mod details via right-click context menu
   - Save current mod configuration as a profile
   - Deploy enabled mods to the game

## Mod Management Features

- **Mod Installation**: Supports ZIP, RAR, and 7Z archives
- **Batch Installation**: Install multiple mods from a folder at once
- **Mod Info Viewing**: View detailed information about each mod including:
  - Basic information (name, ID, version)
  - Authors
  - Dependencies
  - Affected game files
  - Save game compatibility
- **Profile System**: Save and load different mod configurations
- **Conflict Detection**: Currently I check the .modinfo file for each enabled mod
and check if it has any <ImportFile> or <UIScripts> Actions against the same files as other mods.
Im not sure if this is fully correct or if the other actions also need to be checked but this is a
good starting place for now.
- **Easy Deployment**: One-click deployment of enabled mods to game directory

## Technical Details

The application is built using:
- Python with Pyside6 for the GUI
- XML parsing for mod metadata
- Multiple archive format support (ZIP, RAR, 7Z)
- Github Copilot Claude 3.5 (Including this file im very bad at writing haha)

## Requirements

- Python 3.13 or higher
- Additional requirements listed in `requirements.txt`
