import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QListWidget, QLabel, QPushButton, QHBoxLayout
)

class Civ7ModManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Civilization VII Mod Manager")
        self.setGeometry(100, 100, 800, 600)
        
        # Define mods directory path
        self.mods_path = Path(os.getenv('LOCALAPPDATA')) / "Firaxis Games" / "Sid Meier's Civilization VII" / "Mods"
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Add path info
        path_label = QLabel(f"Mods Directory: {self.mods_path}")
        layout.addWidget(path_label)
        
        # Create mod list widget
        self.mod_list = QListWidget()
        layout.addWidget(self.mod_list)
        
        # Buttons layout
        button_layout = QHBoxLayout()
        refresh_button = QPushButton("Refresh Mod List")
        refresh_button.clicked.connect(self.refresh_mod_list)
        button_layout.addWidget(refresh_button)
        layout.addLayout(button_layout)
        
        # Initial mod list population
        self.refresh_mod_list()
    
    def refresh_mod_list(self):
        """Refresh the list of mods from the mods directory"""
        self.mod_list.clear()
        if not self.mods_path.exists():
            self.mod_list.addItem("Mods directory not found!")
            return
            
        try:
            for mod_item in self.mods_path.iterdir():
                if mod_item.is_dir():  # Only list directories as mods
                    self.mod_list.addItem(mod_item.name)
        except Exception as e:
            self.mod_list.addItem(f"Error reading mods: {str(e)}")

def main():
    app = QApplication(sys.argv)
    window = Civ7ModManager()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()