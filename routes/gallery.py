"""
Gallery routes module.
This module handles all gallery-related routes such as displaying images,
uploading images, deleting images, etc.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from utils.date_utils import get_current_time
from utils.image_utils import (
    upload_image, delete_image, get_image_files,
    allowed_file, check_file_size
)

# Create blueprint
gallery_bp = Blueprint('gallery', __name__)


@gallery_bp.route('/gallery')
def gallery_view():
    """Display the gallery page with all images"""
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))
    
    # Get images
    images = get_image_files()
    
    today = get_current_time()
    
    return render_template('gallery.html',
                         images=images,
                         current_year=today.year)


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
            result = upload_image(file, f"{next_number:02d}.jpg")
            
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
        # Delete the image
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