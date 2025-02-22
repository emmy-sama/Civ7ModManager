from PyQt6.QtWidgets import QTreeWidgetItem
from PyQt6.QtCore import Qt

class ModTreeItem(QTreeWidgetItem):
    def __init__(self, mod_info):
        super().__init__()
        self.mod_info = mod_info
        self.update_display()
        
    def update_display(self):
        """Update the item's display text"""
        
        # Column order: Name, ModID, Version, Author, Affects Saves, Has Conflicts
        self.setText(0, self.mod_info.metadata['display_name'])
        self.setText(1, self.mod_info.metadata['id'])
        self.setText(2, self.mod_info.metadata['version'])
        self.setText(3, self.mod_info.metadata['authors'])
        self.setText(4, 'Yes' if self.mod_info.metadata['affects_saves'] else 'No')
        self.setText(5, 'Yes' if self.mod_info.conflicts else 'No')
        self.setForeground(5, Qt.GlobalColor.red if self.mod_info.conflicts else Qt.GlobalColor.white)
        
        self.setCheckState(0, Qt.CheckState.Checked if self.mod_info.enabled else Qt.CheckState.Unchecked)