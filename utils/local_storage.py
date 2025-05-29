"""
Local file storage utility functions.
This module handles all image-related operations with local file storage.
"""

import os
import uuid
import shutil
import logging
from flask import current_app, url_for, send_from_directory
from werkzeug.utils import secure_filename
from config import (
    ALLOWED_EXTENSIONS,
    UPLOAD_FOLDER,
    MAX_CONTENT_LENGTH
)

def ensure_upload_dir():
    """Ensure the upload directory exists
    
    Returns:
        str: Path to upload directory
    """
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    return UPLOAD_FOLDER

def allowed_file(filename):
    """Check if the file type is allowed
    
    Args:
        filename (str): The filename to check
        
    Returns:
        bool: True if file type is allowed, False otherwise
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    
    # Default size limit
    if max_size is None:
        max_size = MAX_CONTENT_LENGTH
    
    if file_size > max_size:
        return False, f"File size ({file_size/1024/1024:.1f}MB) exceeds limit ({max_size/1024/1024:.1f}MB)"
    
    return True, "File size is appropriate"

def upload_image(file, filename=None):
    """Upload image to local storage
    
    Args:
        file (file): The file object to upload
        filename (str, optional): The filename to use
        
    Returns:
        dict: Object with success status, message, and id if successful
    """
    try:
        # Validate file
        if not file:
            return {'success': False, 'message': 'No file provided'}
            
        # Check file extension
        if not allowed_file(file.filename):
            return {'success': False, 'message': 'File type not allowed'}
            
        # Check file size
        size_ok, size_message = check_file_size(file)
        if not size_ok:
            return {'success': False, 'message': size_message}
            
        # Generate unique filename if not provided
        if not filename:
            extension = os.path.splitext(secure_filename(file.filename))[1]
            filename = f"{uuid.uuid4().hex}{extension}"
            
        # Ensure upload directory exists
        upload_dir = ensure_upload_dir()
        
        # Save file
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        return {
            'success': True,
            'message': 'File uploaded successfully',
            'id': filename,
            'url': url_for('gallery.serve_local_image', filename=filename)
        }
    except Exception as e:
        try:
            current_app.logger.error(f"Error uploading file: {e}")
        except RuntimeError:
            logging.error(f"Error uploading file: {e}")
        return {'success': False, 'message': f'Error uploading file: {e}'}

def delete_image(file_id):
    """Delete image from local storage
    
    Args:
        file_id (str): The filename to delete
        
    Returns:
        dict: Object with success status and message
    """
    try:
        # Get file path
        file_path = os.path.join(ensure_upload_dir(), file_id)
        
        # Check if file exists
        if not os.path.exists(file_path):
            return {'success': False, 'message': 'File not found'}
        
        # Delete file
        os.remove(file_path)
        
        return {
            'success': True,
            'message': 'File deleted successfully'
        }
    except Exception as e:
        try:
            current_app.logger.error(f"Error deleting file: {e}")
        except RuntimeError:
            logging.error(f"Error deleting file: {e}")
        return {'success': False, 'message': f'Error deleting file: {e}'}

def get_image_files():
    """Get all images from local storage
    
    Returns:
        list: List of image objects with id and url
    """
    try:
        # Ensure upload directory exists
        upload_dir = ensure_upload_dir()
        
        # List files in directory
        files = []
        for filename in os.listdir(upload_dir):
            if allowed_file(filename):
                files.append({
                    'id': filename,
                    'filename': filename,
                    'url': url_for('gallery.serve_local_image', filename=filename)
                })
        
        return files
    except Exception as e:
        try:
            current_app.logger.error(f"Error getting files: {e}")
        except RuntimeError:
            logging.error(f"Error getting files: {e}")
        return []

def get_image_file(file_id):
    """Get image file from local storage
    
    Args:
        file_id (str): The filename to get
        
    Returns:
        tuple: (file, filename, content_type) or None if file not found
    """
    try:
        # Get file path
        file_path = os.path.join(ensure_upload_dir(), file_id)
        
        # Check if file exists
        if not os.path.exists(file_path):
            return None
        
        # Get content type based on extension
        extension = os.path.splitext(file_id)[1].lower()
        content_type = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif'
        }.get(extension, 'application/octet-stream')
        
        # Return file path (will be read by Flask's send_from_directory)
        return (file_path, file_id, content_type)
    except Exception as e:
        try:
            current_app.logger.error(f"Error getting file: {e}")
        except RuntimeError:
            logging.error(f"Error getting file: {e}")
        return None
