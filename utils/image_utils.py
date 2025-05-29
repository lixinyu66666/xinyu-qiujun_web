"""
Utility functions for image processing and storage using Firebase Storage.
This module handles all image-related operations such as upload, download, delete, 
and retrieval from Firebase Storage.
"""

import os
import imghdr
import uuid
from flask import current_app
from config import (
    USE_FIREBASE_STORAGE, FIREBASE_BUCKET, FIREBASE_KEY_PATH,
    ALLOWED_EXTENSIONS, TEMP_UPLOAD_DIR, IS_VERCEL
)

# Import Firebase libraries conditionally to avoid errors if not installed
try:
    import firebase_admin
    from firebase_admin import credentials, storage
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

# Initialize Firebase Storage
firebase_app = None
firebase_bucket = None

def init_firebase_storage():
    """Initialize Firebase Storage connection
    
    Returns:
        bool: True if Firebase Storage initialized successfully, False otherwise
    """
    global firebase_app, firebase_bucket
    import logging
    
    if not USE_FIREBASE_STORAGE:
        try:
            current_app.logger.info("Firebase Storage is disabled in configuration")
        except RuntimeError:
            logging.info("Firebase Storage is disabled in configuration")
        return False
        
    try:
        if not FIREBASE_AVAILABLE:
            try:
                current_app.logger.error("Firebase libraries not installed")
            except RuntimeError:
                logging.error("Firebase libraries not installed")
            return False
            
        if not os.path.exists(FIREBASE_KEY_PATH):
            try:
                current_app.logger.error(f"Firebase key file not found: {FIREBASE_KEY_PATH}")
            except RuntimeError:
                logging.error(f"Firebase key file not found: {FIREBASE_KEY_PATH}")
            return False
            
        # Check if already initialized
        if firebase_app:
            return True
            
        # Initialize Firebase app
        cred = credentials.Certificate(FIREBASE_KEY_PATH)
        firebase_app = firebase_admin.initialize_app(cred, {
            'storageBucket': FIREBASE_BUCKET
        })
        
        # Get Firebase Storage bucket
        firebase_bucket = storage.bucket()
        try:
            current_app.logger.info("Firebase Storage initialized successfully")
        except RuntimeError:
            logging.info("Firebase Storage initialized successfully")
        return True
        
    except Exception as e:
        try:
            current_app.logger.error(f"Firebase Storage initialization error: {e}")
        except RuntimeError:
            logging.error(f"Firebase Storage initialization error: {e}")
        return False


def allowed_file(filename):
    """Check if the file type is allowed
    
    Args:
        filename (str): The filename to check
        
    Returns:
        bool: True if file type is allowed, False otherwise
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_image(stream):
    """Validate image file format using content
    
    Args:
        stream (file): The file stream to validate
        
    Returns:
        str: The file extension if valid, None otherwise
    """
    header = stream.read(512)
    stream.seek(0)
    format = imghdr.what(None, header)
    if not format:
        return None
    return '.' + (format if format != 'jpeg' else 'jpg')


def check_file_size(file, max_size=None):
    """Check if file size exceeds the limit
    
    Args:
        file (file): The file to check
        max_size (int, optional): The maximum file size in bytes
        
    Returns:
        tuple: (bool, str) indicating if size is OK and a message
    """
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    # Default size limits from config
    if max_size is None:
        if IS_VERCEL:
            max_size = 4 * 1024 * 1024  # 4MB for Vercel
        else:
            max_size = 16 * 1024 * 1024  # 16MB for local
    
    if file_size > max_size:
        return False, f"File size ({file_size/1024/1024:.1f}MB) exceeds limit ({max_size/1024/1024:.1f}MB)"
    
    return True, "File size is appropriate"


def ensure_temp_directory():
    """Ensure temporary directory for uploads exists
    
    Returns:
        str: Path to temporary directory
    """
    if not os.path.exists(TEMP_UPLOAD_DIR):
        os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)
    return TEMP_UPLOAD_DIR


def upload_image(file, filename=None):
    """Upload image to Firebase Storage
    
    Args:
        file (file): The file object to upload
        filename (str, optional): The filename to use
        
    Returns:
        dict: Object with success status, message, and public_url if successful
    """
    if not USE_FIREBASE_STORAGE or not init_firebase_storage():
        return {
            'success': False,
            'message': 'Firebase Storage not configured or initialized'
        }
    
    try:
        # Validate file
        if not file:
            return {'success': False, 'message': 'No file provided'}
            
        # Verify file type
        extension = validate_image(file.stream)
        if not extension:
            return {'success': False, 'message': 'Invalid image file format'}
            
        # Check file size
        size_ok, message = check_file_size(file)
        if not size_ok:
            return {'success': False, 'message': message}
            
        # Generate unique filename if not provided
        if not filename:
            unique_id = uuid.uuid4().hex
            filename = f"{unique_id}{extension}"
        
        # Save to temporary file first
        temp_dir = ensure_temp_directory()
        temp_path = os.path.join(temp_dir, filename)
        file.save(temp_path)
        
        # Upload to Firebase Storage
        blob = firebase_bucket.blob(f"images/{filename}")
        blob.upload_from_filename(temp_path)
        
        # Make the blob publicly accessible
        blob.make_public()
        
        # Remove temporary file
        os.remove(temp_path)
        
        return {
            'success': True,
            'message': 'Image uploaded successfully',
            'filename': filename,
            'public_url': blob.public_url
        }
        
    except Exception as e:
        current_app.logger.error(f"Firebase upload error: {e}")
        return {
            'success': False,
            'message': f"Upload failed: {str(e)}"
        }


def delete_image(filename):
    """Delete image from Firebase Storage
    
    Args:
        filename (str): The filename of the image to delete
        
    Returns:
        dict: Object with success status and message
    """
    if not USE_FIREBASE_STORAGE or not init_firebase_storage():
        return {
            'success': False,
            'message': 'Firebase Storage not configured or initialized'
        }
    
    try:
        # Delete from Firebase Storage
        blob = firebase_bucket.blob(f"images/{filename}")
        blob.delete()
        
        return {
            'success': True,
            'message': 'Image deleted successfully'
        }
        
    except Exception as e:
        current_app.logger.error(f"Firebase delete error: {e}")
        return {
            'success': False,
            'message': f"Delete failed: {str(e)}"
        }


def get_image_files():
    """Get list of image files from Firebase Storage
    
    Returns:
        list: List of image file objects with name, url and other metadata
    """
    if not USE_FIREBASE_STORAGE or not init_firebase_storage():
        return []
    
    try:
        # List all blobs in the 'images' folder
        blobs = firebase_bucket.list_blobs(prefix="images/")
        
        images = []
        for blob in blobs:
            # Skip if not an image file or is a directory
            filename = os.path.basename(blob.name)
            if not allowed_file(filename):
                continue
                
            # Make the blob publicly accessible if not already
            if not blob.public_url:
                blob.make_public()
                
            images.append({
                'name': filename,
                'url': blob.public_url,
                'size': blob.size,
                'updated': blob.updated,
                'metadata': blob.metadata
            })
        
        # Sort by name (which should be numeric)
        images.sort(key=lambda x: x['name'])
        return images
        
    except Exception as e:
        current_app.logger.error(f"Error listing Firebase images: {e}")
        return []


def get_image_url(filename):
    """Get public URL for an image
    
    Args:
        filename (str): The filename of the image
        
    Returns:
        str: Public URL of the image
    """
    if not USE_FIREBASE_STORAGE or not init_firebase_storage():
        return None
    
    try:
        blob = firebase_bucket.blob(f"images/{filename}")
        if blob.exists():
            if not blob.public_url:
                blob.make_public()
            return blob.public_url
        return None
    except Exception as e:
        current_app.logger.error(f"Error getting image URL: {e}")
        return None