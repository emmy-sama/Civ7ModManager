from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import List, Dict, Set

@dataclass
class ModInfo:
    def __init__(self, mod_path):
        self.path = Path(mod_path)
        self.folder_name = self.path.name  # The folder name is our stable identifier
        self.enabled = False
        self.metadata: Dict = {
            'id': '',
            'version': '',
            'display_name': '',  # Changed from 'name' to be more explicit
            'description': '',
            'authors': '',
            'affects_saves': False,
            'dependencies': [],  # List of dependency dicts
            'affected_files': set()  # Set of file paths
        }
        self._load_metadata()

    def _get_localized_name(self, name_tag):
        """Load localized name from the mod's localization file"""
        loc_file_path = self.path / "text" / "en_us" / "ModuleText.xml"
        if not loc_file_path.exists():
            return None

        try:
            tree = ET.parse(loc_file_path)
            root = tree.getroot()
            
            # Look for the name in the localization file
            for row in root.findall('.//EnglishText//Row'):
                tag = row.get('Tag')
                if tag and tag == name_tag:
                    text_element = row.find('.//Text')
                    if text_element is not None and text_element.text:
                        return text_element.text.strip()
        except Exception as e:
            print(f"Error loading localization for {self.folder_name}: {e}")
        return None

    def _load_metadata(self):
        """Load metadata from .modinfo file"""
        # Look for .modinfo file in the mod directory
        modinfo_files = list(self.path.glob("*.modinfo"))
        if not modinfo_files:
            print(f"No .modinfo file found for {self.folder_name}")
            return

        try:
            tree = ET.parse(modinfo_files[0])
            root = tree.getroot()
            
            # Handle XML namespace
            ns = {'': root.tag.split('}')[0].strip('{')} if '}' in root.tag else ''
            if ns:
                ns_prefix = '{' + ns[''] + '}'
            else:
                ns_prefix = ''
            
            # Get basic mod info
            self.metadata['id'] = root.get('id', '')
            self.metadata['version'] = root.get('version', '')
            
            # Get properties
            properties = root.find(f'.//{ns_prefix}Properties')
            if properties is not None:
                name_element = properties.find(f'{ns_prefix}Name')
                if name_element is not None:
                    # First try to get the name directly
                    direct_name = self._get_element_text(properties, f'{ns_prefix}Name')
                    # If the name element has a 'Tag' attribute, try to get localized name
                    if direct_name[0:4] == 'LOC_':
                        localized_name = self._get_localized_name(direct_name)
                        if localized_name:
                            self.metadata['display_name'] = localized_name
                    else:
                        self.metadata['display_name'] = direct_name 
                
                self.metadata['description'] = self._get_element_text(properties, f'{ns_prefix}Description')
                self.metadata['authors'] = self._get_element_text(properties, f'{ns_prefix}Authors')
                affects_saves = self._get_element_text(properties, f'{ns_prefix}AffectsSavedGames')
                self.metadata['affects_saves'] = affects_saves == '1' if affects_saves else False
            
            # If no display name was found in metadata, use folder name
            if not self.metadata['display_name'] or self.metadata['display_name'] == '':
                self.metadata['display_name'] = self.folder_name

            # Get dependencies
            dependencies = root.find(f'.//{ns_prefix}Dependencies')
            if dependencies is not None:
                for dep in dependencies.findall(f'.//{ns_prefix}Mod'):
                    self.metadata['dependencies'].append({
                        'id': dep.get('id', ''),
                        'title': dep.get('title', '')
                    })
            
            # Get affected files from all action groups
            for action_group in root.findall(f'.//{ns_prefix}ActionGroup'):
                actions = action_group.find(f'.//{ns_prefix}Actions')
                if actions is not None:
                    # Process UpdateDatabase actions
                    for update_db in actions.findall(f'.//{ns_prefix}UpdateDatabase'):
                        for item in update_db.findall(f'.//{ns_prefix}Item'):
                            if item.text:
                                self.metadata['affected_files'].add(item.text.strip())
                    
                    # Process UpdateText actions
                    for update_text in actions.findall(f'.//{ns_prefix}UpdateText'):
                        for item in update_text.findall(f'.//{ns_prefix}Item'):
                            if item.text:
                                self.metadata['affected_files'].add(item.text.strip())

        except Exception as e:
            print(f"Error loading metadata for {self.folder_name}: {e}")

    def _get_element_text(self, parent, tag):
        """Helper method to safely get element text"""
        element = parent.find(f'.//{tag}')
        return element.text.strip() if element is not None and element.text else ''