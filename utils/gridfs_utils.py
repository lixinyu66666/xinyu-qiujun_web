"""
GridFS storage utility functions.
This module handles all image-related operations with MongoDB GridFS.
"""

import os
import uuid
import io
import logging
from flask import current_app, url_for
from bson.objectid import ObjectId
from pymongo import MongoClient
from gridfs.synchronous import GridFS
from utils.db import get_db, is_connected
from config import (
    ALLOWED_EXTENSIONS, 
    GRIDFS_COLLECTION, 
    USE_GRIDFS_STORAGE,
    TEMP_UPLOAD_DIR
)

# MongoDB GridFS instances
fs = None

def init_gridfs_storage():
    """Initialize GridFS storage
    
    Returns:
        bool: True if GridFS initialized successfully, False otherwise
    """
    global fs
    if not USE_GRIDFS_STORAGE:
        try:
            current_app.logger.info("GridFS storage is disabled in configuration")
        except RuntimeError:
            logging.info("GridFS storage is disabled in configuration")
        return False
        
    try:
        db = get_db()
        # No need to check db with boolean operation; MongoDB Database objects don't support bool testing
        # Just ensure we have a valid connection
        if not is_connected():
            try:
                current_app.logger.error("MongoDB connection not available for GridFS")
            except RuntimeError:
                logging.error("MongoDB connection not available for GridFS")
            return False
        
        # Create GridFS instance
        fs = GridFS(db, collection=GRIDFS_COLLECTION)
        try:
            current_app.logger.info("GridFS storage initialized successfully")
        except RuntimeError:
            logging.info("GridFS storage initialized successfully")
        return True
    
    except Exception as e:
        try:
            current_app.logger.error(f"GridFS storage initialization error: {e}")
        except RuntimeError:
            logging.error(f"GridFS storage initialization error: {e}")
        return False

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
    
    # Default size limits
    if max_size is None:
        from config import MAX_CONTENT_LENGTH, IS_VERCEL
        if IS_VERCEL:
            max_size = 4 * 1024 * 1024  # 4MB for Vercel
        else:
            max_size = MAX_CONTENT_LENGTH  # Default max file size
    
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
    """Upload image to GridFS
    
    Args:
        file (file): The file object to upload
        filename (str, optional): The filename to use
        
    Returns:
        dict: Object with success status, message, and id if successful
    """
    if not USE_GRIDFS_STORAGE or not init_gridfs_storage():
        return {
            'success': False,
            'message': 'GridFS Storage not configured or initialized'
        }
    
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
            extension = os.path.splitext(file.filename)[1]
            filename = f"{uuid.uuid4().hex}{extension}"
        
        # Save to GridFS
        file_id = fs.put(
            file.read(), 
            filename=filename,
            content_type=file.content_type
        )
        
        return {
            'success': True,
            'message': 'Image uploaded successfully',
            'filename': filename,
            'id': str(file_id),
            'public_url': url_for('gallery.serve_image', file_id=str(file_id), _external=True)
        }
        
    except Exception as e:
        current_app.logger.error(f"GridFS upload error: {e}")
        return {
            'success': False,
            'message': f"Upload failed: {str(e)}"
        }

def delete_image(file_id):
    """Delete image from GridFS
    
    Args:
        file_id (str): The ID of the file to delete
        
    Returns:
        dict: Object with success status and message
    """
    if not USE_GRIDFS_STORAGE or not init_gridfs_storage():
        return {
            'success': False,
            'message': 'GridFS Storage not configured or initialized'
        }
    
    try:
        # Convert string ID to ObjectId
        obj_id = ObjectId(file_id)
        
        # Check if file exists
        if not fs.exists(obj_id):
            return {
                'success': False,
                'message': 'File not found'
            }
        
        # Delete file
        fs.delete(obj_id)
        
        return {
            'success': True,
            'message': 'Image deleted successfully'
        }
        
    except Exception as e:
        current_app.logger.error(f"GridFS delete error: {e}")
        return {
            'success': False,
            'message': f"Delete failed: {str(e)}"
        }

def get_image_files():
    """Get list of image files from GridFS
    
    Returns:
        list: List of image file objects with name, id and other metadata
    """
    if not USE_GRIDFS_STORAGE or not init_gridfs_storage():
        return []
    
    try:
        # Find all files in GridFS
        files = []
        for grid_out in fs.find():
            # Skip files without filenames
            if not hasattr(grid_out, 'filename'):
                continue
                
            # Skip if not an image file
            if not allowed_file(grid_out.filename):
                continue
                
            files.append({
                'name': grid_out.filename,
                'id': str(grid_out._id),
                'url': url_for('gallery.serve_image', file_id=str(grid_out._id), _external=True),
                'size': grid_out.length,
                'updated': grid_out.upload_date,
                'content_type': grid_out.content_type
            })
        
        # Sort by upload date (newest first)
        files.sort(key=lambda x: x['updated'], reverse=True)
        
        return files
        
    except Exception as e:
        current_app.logger.error(f"Error listing GridFS images: {e}")
        return []

def get_image_file(file_id):
    """Get an image file from GridFS by its ID
    
    Args:
        file_id (str): The ID of the file to retrieve
        
    Returns:
        tuple: (file_data, filename, content_type) or None if not found
    """
    if not USE_GRIDFS_STORAGE or not init_gridfs_storage():
        return None
    
    try:
        # Convert string ID to ObjectId
        obj_id = ObjectId(file_id)
        
        # Check if file exists
        if not fs.exists(obj_id):
            return None
        
        # Get file
        grid_out = fs.get(obj_id)
        
        # Return file data
        return grid_out.read(), grid_out.filename, grid_out.content_type
    
    except Exception as e:
        current_app.logger.error(f"Error getting GridFS image: {e}")
        return None
