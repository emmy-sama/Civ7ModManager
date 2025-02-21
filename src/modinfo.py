import xml.etree.ElementTree as ET

from pathlib import Path
from typing import List, Dict

class ModInfo:
    def __init__(self, mod_path: Path):
        self.path = mod_path
        self.folder_name = self.path.name
        self.enabled = False
        self.conflicts: Dict[str, List[str]] = {}
        self.metadata: Dict = {
            'id': '',
            'version': '',
            'display_name': '',
            'authors': '',
            'affects_saves': False,
            'dependencies': [],
            'affected_files': set()
        }
        self._load_metadata()

    

    def _load_metadata(self):
        """Load metadata from .modinfo file"""
        
        try:
            # Look for .modinfo file in the mod directory
            modinfo_files = list(self.path.glob("*.modinfo"))
            if not modinfo_files: 
                raise FileNotFoundError(f'No .modinfo file found for {self.folder_name}')
            
            tree = ET.parse(modinfo_files[0])
            root = tree.getroot()
            if root is None:
                raise ET.ParseError('Root element not found')
            
            # Handle XML namespace
            ns = {'': root.tag.split('}')[0].strip('{')} if '}' in root.tag else ''
            if ns:
                ns_prefix = '{' + ns[''] + '}'
            else:
                ns_prefix = ''
            
            # Get basic mod info
            id = root.get('id', '')
            if id == '':
                raise ET.ParseError('ID attribute not found')
            
            version= root.get('version', '')
            
            # Get properties
            properties = root.find(f'.//{ns_prefix}Properties')
            if properties is None:
                raise ET.ParseError('Properties element not found')
            
            # First try to get the name directly
            final_name = self.folder_name
            direct_name: ET.Element | None = properties.find(f'{ns_prefix}Name')
            if direct_name is None:
                raise ET.ParseError('Name element not found')
            
            # If the name element starts with LOC_ try to get localized name
            if direct_name[0:4] == 'LOC_':
                localized_name = self._get_localized_name(direct_name)
                if localized_name:
                    final_name = localized_name
            
            affects_saves = properties.find(f'{ns_prefix}AffectsSavedGames')
            if affects_saves is None:
                raise ET.ParseError('AffectsSavedGames element not found')
            
            # Get dependencies
            dependencies_list = []
            dependencies = root.find(f'.//{ns_prefix}Dependencies')
            
            if dependencies is not None:
                for dep in dependencies.findall(f'.//{ns_prefix}Mod'):
                    dependencies_list.append({
                        'id': dep.get('id', ''),
                        'title': dep.get('title', '')
                    })
            
            # Get affected files from all action groups
            update_db_set = set()
            update_text_set = set()
            ui_scripts_set = set()
            import_files_set = set()
            
            for action_group in root.findall(f'.//{ns_prefix}ActionGroup'):
                actions = action_group.find(f'.//{ns_prefix}Actions')
                if actions is not None:
                    # Process UpdateDatabase actions
                    for update_db in actions.findall(f'.//{ns_prefix}UpdateDatabase'):
                        for item in update_db.findall(f'.//{ns_prefix}Item'):
                            if item.text:
                                update_db_set.add(item.text.strip())
                    
                    # Process UpdateText actions
                    for update_text in actions.findall(f'.//{ns_prefix}UpdateText'):
                        for item in update_text.findall(f'.//{ns_prefix}Item'):
                            if item.text:
                                update_text_set.add(item.text.strip())
                                             
                    # Process UIScripts actions
                    for ui_scripts in actions.findall(f'.//{ns_prefix}UIScripts'):
                        for item in ui_scripts.findall(f'.//{ns_prefix}Item'):
                            if item.text:
                                ui_scripts_set.add(item.text.strip())
                                
                    # Process ImportFiles actions
                    for import_files in actions.findall(f'.//{ns_prefix}ImportFiles'):
                        for item in import_files.findall(f'.//{ns_prefix}Item'):
                            if item.text:
                                import_files_set.add(item.text.strip())
            
            if not update_db_set and not update_text_set and not ui_scripts_set and not import_files_set:
                raise ET.ParseError('No affected files found')
            
            # Set metadata now that we should have all required info
            self.metadata['id'] = id
            self.metadata['version'] = version
            self.metadata['display_name'] = final_name
            self.metadata['authors'] = self._get_element_text(properties, f'{ns_prefix}Authors')
            self.metadata['affects_saves'] = affects_saves == '1' if affects_saves else False
            self.metadata['dependencies'] = dependencies_list
            # Not sure if we need update_db or update_text
            self.metadata['affected_files'] = ui_scripts_set | import_files_set #| update_db_set | update_text_set
            
        except Exception as e:
            print(f"Error loading metadata for {self.folder_name}: {e}")
            self.metadata['display_name'] = self.folder_name
            self.metadata['id'] = "ModInfo File Broken"

    def _get_element_text(self, parent, tag) -> str:
        """Helper method to safely get element text"""
        
        element = parent.find(f'.//{tag}')
        return element.text.strip() if element is not None and element.text else ''

    def _get_localized_name(self, name_tag: ET.Element) -> str | None:
        """Load localized name from the mod's localization file"""
        
        loc_file_path = self.path / "text" / "en_us" / "ModuleText.xml"
        if not loc_file_path.exists():
            raise FileNotFoundError
        
        try:
            tree = ET.parse(loc_file_path)
            root = tree.getroot()
            if root is None:
                raise ET.ParseError('Root element not found')
            
            # Look for the name in the localization file
            for row in root.findall('.//EnglishText//Row'):
                tag = row.get('Tag')
                if tag and tag == name_tag:
                    return self._get_element_text(row, 'Text')
            return None
                
        except FileNotFoundError:
            print(f"Localization file not found for {self.folder_name}")
            return None
                    
        except ET.ParseError as e:
            print(f"Error parsing localization for {self.folder_name}: {e}")
            return None
        
        except Exception as e:
            print(f"Error loading localization for {self.folder_name}: {e}")
            return None