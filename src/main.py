"""Main application entry point for the Civilization VII Mod Manager"""
import sys
from app import Civ7ModManagerApp

if __name__ == "__main__":
    app = Civ7ModManagerApp(sys.argv)
    app.run()