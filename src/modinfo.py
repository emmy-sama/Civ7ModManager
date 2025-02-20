from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

@dataclass
class ModInfo:
    def __init__(self, mod_path):
        self.path = Path(mod_path)
        self.name = self.path.name
        self.enabled = False
        self.metadata = {
            'id': '',
            'version': '',
            'name': '',
            'description': '',
            'authors': '',
            'affects_saves': False,
            'dependencies': [],
            'affected_files': set()
        }
        self._load_metadata()

    def _load_metadata(self):
        """Load metadata from .modinfo file"""
        # Look for .modinfo file in the mod directory
        modinfo_files = list(self.path.glob("*.modinfo"))
        if not modinfo_files:
            print(f"No .modinfo file found for {self.name}")
            return

        try:
            tree = ET.parse(modinfo_files[0])
            root = tree.getroot()
            
            # Get basic mod info
            self.metadata['id'] = root.get('id', '')
            self.metadata['version'] = root.get('version', '')
            
            # Get properties
            properties = root.find('.//Properties')
            if properties is not None:
                self.metadata['name'] = self._get_element_text(properties, 'Name')
                print(self.metadata['name'])
                self.name = self.metadata['name']  # Use mod name from .modinfo
                self.metadata['description'] = self._get_element_text(properties, 'Description')
                self.metadata['authors'] = self._get_element_text(properties, 'Authors')
                affects_saves = self._get_element_text(properties, 'AffectsSavedGames')
                self.metadata['affects_saves'] = affects_saves == '1' if affects_saves else False
            
            # Get dependencies
            dependencies = root.find('.//Dependencies')
            if dependencies is not None:
                for dep in dependencies.findall('Mod'):
                    self.metadata['dependencies'].append({
                        'id': dep.get('id', ''),
                        'title': dep.get('title', '')
                    })
            
            # Get affected files
            for action_group in root.findall('.//ActionGroup'):
                for action in action_group.findall('.//Actions'):
                    # UI Scripts
                    for script in action.findall('.//UIScripts/Item'):
                        if script.text:
                            self.metadata['affected_files'].add(script.text)
                    
                    # Localization files
                    for text_file in action.findall('.//LocalizedText/File'):
                        if text_file.text:
                            self.metadata['affected_files'].add(text_file.text)

        except Exception as e:
            print(f"Error loading metadata for {self.name}: {e}")

    def _get_element_text(self, parent, tag):
        """Helper method to safely get element text"""
        element = parent.find(tag)
        return element.text if element is not None else ''