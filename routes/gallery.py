"""
Gallery routes module.
This module handles all gallery-related routes such as displaying images,
uploading images, deleting images, etc.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, send_file, Response, send_from_directory
from utils.date_utils import get_current_time
import io
import os

from config import USE_GRIDFS_STORAGE

# Import appropriate storage module based on configuration
if USE_GRIDFS_STORAGE:
    from utils.gridfs_utils import (
        upload_image,
        delete_image,
        get_image_files,
        get_image_file,
        allowed_file, 
        check_file_size
    )
else:
    from utils.local_storage import (
        upload_image,
        delete_image,
        get_image_files,
        get_image_file,
        allowed_file, 
        check_file_size
    )

# Create blueprint
gallery_bp = Blueprint('gallery', __name__)


@gallery_bp.route('/gallery')
def gallery_view():
    """Display the gallery page with all images"""
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))
    
    # Get images from GridFS
    images = get_image_files()
    
    today = get_current_time()
    
    return render_template('gallery.html',
                         images=images,
                         current_year=today.year)


@gallery_bp.route('/images/<file_id>')
def serve_image(file_id):
    """Serve an image from storage by its ID
    
    Args:
        file_id (str): The ID of the image to serve
        
    Returns:
        Response: The image file
    """
    if USE_GRIDFS_STORAGE:
        # Serve from GridFS
        result = get_image_file(file_id)
        if not result:
            current_app.logger.error(f"Image not found: {file_id}")
            return "Image not found", 404
            
        grid_out, filename, content_type = result
        response = Response(grid_out, mimetype=content_type)
        
        # Set content disposition header so browser knows how to handle the file
        if filename:
            response.headers.set(
                'Content-Disposition', 'inline', filename=filename
            )
        
        return response
    else:
        # For local storage, redirect to local_image route
        return redirect(url_for('gallery.serve_local_image', filename=file_id))


@gallery_bp.route('/local-images/<filename>')
def serve_local_image(filename):
    """Serve an image from local storage by its filename
    
    Args:
        filename (str): The filename of the image to serve
        
    Returns:
        Response: The image file
    """
    from config import UPLOAD_FOLDER
    return send_from_directory(UPLOAD_FOLDER, filename)
    
    # Get image from GridFS
    result = get_image_file(file_id)
    
    if result is None:
        return "Image not found", 404
        
    file_data, filename, content_type = result
    
    # Create response with image data
    return Response(
        file_data,
        mimetype=content_type,
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )


@gallery_bp.route('/upload', methods=['POST'])
def upload():
    """Upload a new image
    
    Handles image upload form submission
    """
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))

    if 'image' not in request.files:
        flash('没有选择文件')
        return redirect(url_for('gallery.gallery_view'))
    
    file = request.files['image']
    if file.filename == '':
        flash('没有选择文件')
        return redirect(url_for('gallery.gallery_view'))

    if file and allowed_file(file.filename):
        # Check file size
        size_ok, message = check_file_size(file)
        if not size_ok:
            flash(f'图片太大: {message}')
            current_app.logger.warning(f"Image upload failed: {message}")
            return redirect(url_for('gallery.gallery_view'))
        
        try:
            # Get current images to determine next number
            images = get_image_files()
            next_number = len(images) + 1
            
            # Generate filename with sequential number
            new_filename = f"{next_number:02d}.jpg"
            
            # Upload image to GridFS
            result = upload_image(file, new_filename)
            
            if result['success']:
                flash('图片上传成功')
                current_app.logger.info(f"Image upload successful: {result['filename']}")
            else:
                flash(f'图片上传失败: {result["message"]}')
                current_app.logger.error(f"Image upload failed: {result['message']}")
            
            return redirect(url_for('gallery.gallery_view'))
            
        except Exception as e:
            current_app.logger.error(f"Image upload error: {str(e)}")
            flash('图片上传失败: 服务器错误')
            return redirect(url_for('gallery.gallery_view'))
    
    flash('不支持的文件类型')
    return redirect(url_for('gallery.gallery_view'))


@gallery_bp.route('/storage-test')
def storage_test():
    """Test the storage configuration"""
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))
    
    # Test storage configuration
    storage_config = {
        'USE_GRIDFS_STORAGE': USE_GRIDFS_STORAGE,
    }
    
    # Test GridFS connection
    from utils.gridfs_utils import init_gridfs_storage, fs
    gridfs_initialized = init_gridfs_storage()
    storage_config['GridFS_Initialized'] = gridfs_initialized
    storage_config['GridFS_Object'] = "Available" if fs else "Not Available"
    
    # Get the list of available images
    try:
        images = get_image_files()
        storage_config['Images_Found'] = len(images)
        if len(images) > 0:
            storage_config['Sample_Image'] = images[0]
    except Exception as e:
        storage_config['Error'] = str(e)
    
    # Build HTML response
    import html
    response = "<html><head><title>Storage Test</title></head><body>"
    response += "<h1>Storage Configuration Test</h1>"
    response += "<table border='1'>"
    for key, value in storage_config.items():
        response += f"<tr><td>{html.escape(key)}</td><td>{html.escape(str(value))}</td></tr>"
    response += "</table>"
    
    if 'Sample_Image' in storage_config:
        sample = storage_config['Sample_Image']
        response += f"<h2>Sample Image Test</h2>"
        response += f"<img src='{sample['url']}' style='max-width: 300px;'>"
    
    response += "<p><a href='/gallery'>Back to Gallery</a></p>"
    response += "</body></html>"
    
    return response


@gallery_bp.route('/delete', methods=['POST'])
def delete():
    """Delete an image
    
    Handles image deletion form submission
    """
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))
    
    image = request.form.get('image')
    if not image:
        flash('未指定要删除的图片')
        return redirect(url_for('gallery.gallery_view'))
    
    try:
        # Delete the image from GridFS
        result = delete_image(image)
        
        if result['success']:
            flash('图片已删除')
            current_app.logger.info(f"Image deleted: {image}")
        else:
            flash(f'删除图片失败: {result["message"]}')
            current_app.logger.error(f"Image deletion failed: {result['message']}")
        
        # Renumber remaining images (to be implemented if needed)
        # This would require downloading all images, renaming, and re-uploading
        
        return redirect(url_for('gallery.gallery_view'))
        
    except Exception as e:
        current_app.logger.error(f"Error deleting image: {str(e)}")
        flash('删除图片时出错')
        return redirect(url_for('gallery.gallery_view'))