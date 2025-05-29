"""
Journal routes module.
This module handles all journal-related routes such as viewing entries,
adding entries, editing entries, etc.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from utils.date_utils import get_current_time
from models.journal import (
    get_all_entries, get_entry_by_id, create_entry, update_entry, delete_entry
)

# Create blueprint
journal_bp = Blueprint('journal', __name__)


@journal_bp.route('/journal')
def journal_list():
    """Display list of journal entries"""
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))
    
    # Get sort parameter from query string
    sort = request.args.get('sort', 'newest')
    
    # Get entries with appropriate sorting
    if sort == 'oldest':
        entries = get_all_entries('timestamp', False)
    else:  # default to newest
        entries = get_all_entries('timestamp', True)
    
    today = get_current_time()
    
    return render_template('journal.html',
                         entries=entries,
                         current_year=today.year)


@journal_bp.route('/add_entry', methods=['GET', 'POST'])
def add_entry():
    """Add a new journal entry
    
    GET: Display add entry form
    POST: Process form submission and create new entry
    """
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))

    if request.method == 'GET':
        today = get_current_time()
        return render_template('add_entry.html', current_year=today.year)
    
    # Process POST request
    try:
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        author = request.form.get('author', '').strip()
        
        if not all([title, content, author]):
            flash('请填写所有必填字段')
            return redirect(url_for('journal.add_entry'))
        
        current_app.logger.info(f"Attempting to add entry: {title} by {author}")
        
        # Create entry
        entry_data = {
            'title': title,
            'content': content,
            'author': author
        }
        
        success, entry_id, error = create_entry(entry_data)
        
        if success:
            flash('日志添加成功')
        else:
            flash(f'保存日志时出错: {error if error else "请稍后重试"}')
        
        return redirect(url_for('journal.journal_list'))
        
    except Exception as e:
        current_app.logger.error(f"Error adding entry: {str(e)}")
        flash('添加日志时发生错误，请联系管理员')
        return redirect(url_for('journal.add_entry'))


@journal_bp.route('/edit/<id>')
def edit(id):
    """Display form to edit an existing journal entry
    
    Args:
        id: Entry ID to edit
    """
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))
    
    entry = get_entry_by_id(id)
    if not entry:
        flash('找不到指定的日志')
        return redirect(url_for('journal.journal_list'))
    
    today = get_current_time()
    return render_template('edit_entry.html', 
                         entry=entry,
                         current_year=today.year)


@journal_bp.route('/update/<id>', methods=['POST'])
def update(id):
    """Update an existing journal entry
    
    Args:
        id: Entry ID to update
    """
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))
    
    title = request.form.get('title')
    content = request.form.get('content')
    author = request.form.get('author')
    
    if not all([title, content, author]):
        flash('请填写所有必填字段')
        return redirect(url_for('journal.edit', id=id))
    
    try:
        entry_data = {
            'title': title,
            'content': content,
            'author': author
        }
        
        success, error = update_entry(id, entry_data)
        
        if success:
            flash('日志已更新')
        else:
            flash(f'更新日志时出错: {error if error else "请稍后重试"}')
        
        return redirect(url_for('journal.view', id=id))
        
    except Exception as e:
        current_app.logger.error(f"Error updating entry: {str(e)}")
        flash('更新日志时发生错误，请联系管理员')
        return redirect(url_for('journal.edit', id=id))


@journal_bp.route('/delete_entry', methods=['POST'])
def delete():
    """Delete a journal entry"""
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))
    
    entry_id = request.form.get('entry_id')
    if not entry_id:
        return redirect(url_for('journal.journal_list'))
    
    try:
        current_app.logger.info(f"Attempting to delete entry: {entry_id}")
        
        success, error = delete_entry(entry_id)
        
        if success:
            flash('日志已删除')
        else:
            flash(f'删除日志时出错: {error if error else "请稍后重试"}')
        
        return redirect(url_for('journal.journal_list'))
        
    except Exception as e:
        current_app.logger.error(f"Error deleting entry: {str(e)}")
        flash('删除日志时发生错误，请联系管理员')
        return redirect(url_for('journal.journal_list'))


@journal_bp.route('/view/<id>')
def view(id):
    """View a specific journal entry
    
    Args:
        id: Entry ID to view
    """
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))
    
    entry = get_entry_by_id(id)
    if not entry:
        flash('找不到指定的日志')
        return redirect(url_for('journal.journal_list'))
    
    today = get_current_time()
    return render_template('view_entry.html', 
                         entry=entry,
                         current_year=today.year)