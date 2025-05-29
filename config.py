"""
Configuration file for the application.
"""

import os
import pytz
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define China timezone
CHINA_TIMEZONE = pytz.timezone('Asia/Shanghai')

# Check if running in a Vercel environment
IS_VERCEL = os.environ.get('VERCEL') == '1'

# Set password from environment variable
PASSWORD = os.getenv('PASSWORD', 'default_password')

# Set relationship anniversary date
LOVE_START_DATE = datetime(2022, 12, 10, tzinfo=CHINA_TIMEZONE)

# Flask app configuration
SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24))

# MongoDB connection settings
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("MONGODB_DB", "journal_db")
JOURNAL_COLLECTION = "entries"

# File paths and directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
IMAGES_DIR = os.path.join(STATIC_DIR, 'images')
JOURNAL_FILE = os.path.join(BASE_DIR, 'data/journal.json')

# Upload configuration
UPLOAD_FOLDER = IMAGES_DIR
if IS_VERCEL:
    TEMP_UPLOAD_DIR = '/tmp/images'
    UPLOAD_FOLDER = TEMP_UPLOAD_DIR
    JOURNAL_FILE = '/tmp/journal.json'
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # 4MB (Vercel limit)
else:
    TEMP_UPLOAD_DIR = os.path.join(BASE_DIR, 'tmp')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'JPG', 'JPEG', 'PNG', 'GIF'}

# Storage Configuration
USE_GRIDFS_STORAGE = os.getenv('USE_GRIDFS_STORAGE', 'true').lower() == 'true'
GRIDFS_COLLECTION = 'images'