"""
Utilities package initialization.
This module contains utility functions and helpers for the application.
"""

# Import utility functions for easier access
from utils.db import init_mongodb_connection, is_connected
from utils.date_utils import get_current_time, format_date, format_time
from utils.file_utils import ensure_directory_exists, read_json_file, write_json_file

# Import storage modules based on configuration
from config import USE_GRIDFS_STORAGE
if USE_GRIDFS_STORAGE:
    from utils.gridfs_utils import init_gridfs_storage
# Local storage doesn't need initialization