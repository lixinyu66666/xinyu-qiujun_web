"""
Main application entry point.
This module initializes and configures the Flask application.
"""

from flask import Flask
import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import utility functions
from utils.db import init_mongodb_connection
from utils.image_utils import init_firebase_storage
from config import SECRET_KEY, LOG_DIR

# Create Flask application
app = Flask(__name__)
app.secret_key = SECRET_KEY

# Set up logging
def setup_logging():
    """Configure application logging
    
    Sets up rotating file handler for logging
    """
    # Ensure log directory exists
    if not os.path.exists(LOG_DIR):
        try:
            os.makedirs(LOG_DIR)
        except Exception as e:
            print(f"Unable to create log directory: {e}")
            return False

    # Configure log handler
    try:
        handler = RotatingFileHandler(os.path.join(LOG_DIR, 'app.log'), maxBytes=10240, backupCount=5)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Application started')
        return True
    except Exception as e:
        print(f"Unable to configure logging: {e}")
        return False

# Initialize logging
setup_logging()

# Configure application settings from config
from config import MAX_CONTENT_LENGTH, IS_VERCEL

# Configure file upload size limit
if IS_VERCEL:
    app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024  # 4MB max file size for Vercel
else:
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH  # Default max file size

# Register all routes with the application
def register_routes_with_app():
    """Register blueprints and routes with the application"""
    from routes import register_routes
    register_routes(app)

# Create application context for initialization
with app.app_context():
    # Initialize MongoDB connection
    init_mongodb_connection()
    
    # Initialize Firebase Storage
    init_firebase_storage()

# Register routes with the application
register_routes_with_app()

# Application instance for Vercel (required for Vercel deployment)
application = app

# Run the application if executed directly
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)