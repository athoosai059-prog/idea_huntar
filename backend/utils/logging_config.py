"""
Logging configuration for IdeaHunter.
Provides structured logging with different levels and formatters.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
import os

# Create logs directory
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Log file paths
LOG_FILE = LOG_DIR / "ideahunter.log"
ERROR_LOG_FILE = LOG_DIR / "error.log"

# Log format
DETAILED_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
SIMPLE_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
CONSOLE_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# Date format
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def setup_logging(log_level='INFO', log_to_file=True, log_to_console=True):
    """
    Setup logging configuration for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_to_console: Whether to log to console
    """
    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(DETAILED_FORMAT, datefmt=DATE_FORMAT)
    simple_formatter = logging.Formatter(SIMPLE_FORMAT, datefmt=DATE_FORMAT)
    console_formatter = logging.Formatter(CONSOLE_FORMAT, datefmt=DATE_FORMAT)

    # File handler - all logs
    if log_to_file:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)

        # Error file handler - only errors
        error_handler = RotatingFileHandler(
            ERROR_LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)


def get_logger(name):
    """
    Get a logger with the specified name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Setup default logging
setup_logging(
    log_level=os.getenv('LOG_LEVEL', 'INFO'),
    log_to_file=os.getenv('LOG_TO_FILE', 'true').lower() == 'true',
    log_to_console=os.getenv('LOG_TO_CONSOLE', 'true').lower() == 'true'
)