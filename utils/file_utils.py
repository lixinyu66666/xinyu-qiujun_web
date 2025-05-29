import os
import json
from flask import current_app
from config import BASE_DIR

def ensure_directory_exists(directory):
    """Ensure directory exists"""
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

def read_json_file(file_path):
    """Read JSON data from file"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        current_app.logger.error(f"Error reading JSON file: {e}")
        return []

def write_json_file(file_path, data):
    """Write JSON data to file"""
    try:
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        current_app.logger.error(f"Error writing JSON file: {e}")
        return False