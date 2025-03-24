"""Logging configuration for the Civilization VII Mod Manager"""
import logging
from datetime import datetime
from pathlib import Path

def init_logging(logs_path: Path) -> logging.Logger:
    """Initialize logging configuration
    
    Args:
        logs_path: Path to the directory where log files should be stored
        
    Returns:
        Logger: Configured logger instance
    """
    logger = logging.getLogger("Civ7ModManager")
    logger.setLevel(logging.DEBUG)

    # File handler with debug level
    log_file = logs_path / f"modmanager_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)

    # Console handler for immediate feedback
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(
        "%(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(console_handler)

    return logger