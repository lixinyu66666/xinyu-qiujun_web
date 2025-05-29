"""
Journal model and database operations.
This module handles all journal entry-related operations such as
create, read, update, and delete (CRUD).
"""

import os
import json
from datetime import datetime
from flask import current_app
from utils.db import get_collection, is_connected
from utils.file_utils import read_json_file, write_json_file
from utils.date_utils import get_current_time
from config import JOURNAL_COLLECTION, IS_VERCEL

# Journal file path - used when MongoDB is not available
JOURNAL_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data/journal.json')
if IS_VERCEL:
    # Use /tmp directory on Vercel when MongoDB is not available
    JOURNAL_FILE = '/tmp/journal.json'

class JournalEntry:
    """Journal entry model class"""
    
    def __init__(self, id=None, title="", content="", author="", date=None, 
                 time=None, timestamp=None):
        """Initialize a journal entry
        
        Args:
            id (str): Entry ID, defaults to current timestamp
            title (str): Entry title
            content (str): Entry content
            author (str): Entry author
            date (str): Formatted date string
            time (str): Formatted time string
            timestamp (float): Unix timestamp
        """
        now = get_current_time()
        
        self.id = id if id else str(int(now.timestamp()))
        self.title = title
        self.content = content
        self.author = author
        self.date = date if date else now.strftime('%Y年%m月%d日')
        self.time = time if time else now.strftime('%H:%M:%S')
        self.timestamp = timestamp if timestamp else now.timestamp()
    
    def to_dict(self):
        """Convert entry to dictionary
        
        Returns:
            dict: Dictionary representation of entry
        """
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'author': self.author,
            'date': self.date,
            'time': self.time,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create entry from dictionary
        
        Args:
            data (dict): Dictionary representation of entry
            
        Returns:
            JournalEntry: New journal entry instance
        """
        return cls(
            id=data.get('id'),
            title=data.get('title', ''),
            content=data.get('content', ''),
            author=data.get('author', ''),
            date=data.get('date'),
            time=data.get('time'),
            timestamp=data.get('timestamp')
        )


def get_all_entries(sort_key='timestamp', sort_desc=True):
    """Get all journal entries
    
    Args:
        sort_key (str): Key to sort by
        sort_desc (bool): Sort in descending order if True, ascending if False
        
    Returns:
        list: List of journal entries as dictionaries
    """
    # If MongoDB is available, load from database
    if is_connected():
        collection = get_collection(JOURNAL_COLLECTION)
        sort_direction = -1 if sort_desc else 1
        entries = list(collection.find({}, {'_id': 0}).sort(sort_key, sort_direction))
        return entries
    
    # Otherwise load from local file
    entries = read_json_file(JOURNAL_FILE)
    
    # Sort entries
    if sort_desc:
        entries.sort(key=lambda x: x.get(sort_key, 0), reverse=True)
    else:
        entries.sort(key=lambda x: x.get(sort_key, 0))
        
    return entries


def get_entry_by_id(entry_id):
    """Get journal entry by ID
    
    Args:
        entry_id (str): Entry ID
        
    Returns:
        dict: Journal entry or None if not found
    """
    # If MongoDB is available, query from database
    if is_connected():
        collection = get_collection(JOURNAL_COLLECTION)
        entry = collection.find_one({'id': entry_id}, {'_id': 0})
        return entry
    
    # Otherwise search in file
    entries = read_json_file(JOURNAL_FILE)
    for entry in entries:
        if entry.get('id') == entry_id:
            return entry
    
    return None


def create_entry(entry_data):
    """Create new journal entry
    
    Args:
        entry_data (dict): Journal entry data
        
    Returns:
        tuple: (success, entry_id, error_message)
    """
    try:
        # Create entry object
        entry = JournalEntry(
            title=entry_data.get('title', ''),
            content=entry_data.get('content', ''),
            author=entry_data.get('author', '')
        )
        
        entry_dict = entry.to_dict()
        entry_id = entry_dict['id']
        
        # If MongoDB is available, save to database
        if is_connected():
            collection = get_collection(JOURNAL_COLLECTION)
            result = collection.insert_one(entry_dict)
            if result.inserted_id:
                current_app.logger.info(f"Entry successfully added to MongoDB: {entry_id}")
                return True, entry_id, None
            else:
                error = "MongoDB insert did not return ID"
                current_app.logger.warning(f"{error}: {entry_id}")
                # Fall back to file storage
        
        # MongoDB unavailable or insert failed, use file storage
        entries = read_json_file(JOURNAL_FILE)
        entries.append(entry_dict)
        
        if write_json_file(JOURNAL_FILE, entries):
            current_app.logger.info(f"Entry added to file storage: {entry_id}")
            return True, entry_id, None
        else:
            error = "Failed to save to file storage"
            current_app.logger.error(f"{error}: {entry_id}")
            return False, entry_id, error
            
    except Exception as e:
        error = f"Error creating entry: {str(e)}"
        current_app.logger.error(error)
        return False, None, error


def update_entry(entry_id, entry_data):
    """Update journal entry
    
    Args:
        entry_id (str): Entry ID
        entry_data (dict): Updated entry data
        
    Returns:
        tuple: (success, error_message)
    """
    try:
        # If MongoDB is available, update in database
        if is_connected():
            collection = get_collection(JOURNAL_COLLECTION)
            
            # Update timestamp to current time
            now = get_current_time()
            entry_data['date'] = now.strftime('%Y年%m月%d日')
            entry_data['time'] = now.strftime('%H:%M:%S')
            entry_data['timestamp'] = now.timestamp()
            
            result = collection.update_one(
                {'id': entry_id},
                {'$set': entry_data}
            )
            
            if result.modified_count > 0:
                current_app.logger.info(f"Entry successfully updated in MongoDB: {entry_id}")
                return True, None
            elif result.matched_count > 0:
                # Document found but not modified (no changes)
                current_app.logger.info(f"Entry found but not modified in MongoDB: {entry_id}")
                return True, None
            else:
                current_app.logger.warning(f"Entry to update not found in MongoDB: {entry_id}")
                # Fall back to file storage
        
        # MongoDB unavailable or update failed, use file storage
        entries = read_json_file(JOURNAL_FILE)
        entry_found = False
        
        for i, entry in enumerate(entries):
            if entry.get('id') == entry_id:
                # Update entry fields while preserving id
                entries[i].update(entry_data)
                
                # Update timestamp
                now = get_current_time()
                entries[i]['date'] = now.strftime('%Y年%m月%d日')
                entries[i]['time'] = now.strftime('%H:%M:%S')
                entries[i]['timestamp'] = now.timestamp()
                
                entry_found = True
                break
        
        if not entry_found:
            error = f"Entry to update not found: {entry_id}"
            current_app.logger.warning(error)
            return False, error
        
        if write_json_file(JOURNAL_FILE, entries):
            current_app.logger.info(f"Entry updated in file storage: {entry_id}")
            return True, None
        else:
            error = "Failed to save updated entry to file storage"
            current_app.logger.error(f"{error}: {entry_id}")
            return False, error
            
    except Exception as e:
        error = f"Error updating entry: {str(e)}"
        current_app.logger.error(error)
        return False, error


def delete_entry(entry_id):
    """Delete journal entry
    
    Args:
        entry_id (str): Entry ID
        
    Returns:
        tuple: (success, error_message)
    """
    try:
        # If MongoDB is available, delete from database
        if is_connected():
            collection = get_collection(JOURNAL_COLLECTION)
            result = collection.delete_one({'id': entry_id})
            
            if result.deleted_count > 0:
                current_app.logger.info(f"Entry successfully deleted from MongoDB: {entry_id}")
                return True, None
            else:
                current_app.logger.warning(f"Entry to delete not found in MongoDB: {entry_id}")
                # Fall back to file storage
        
        # MongoDB unavailable or delete failed, use file storage
        entries = read_json_file(JOURNAL_FILE)
        original_count = len(entries)
        entries = [entry for entry in entries if entry.get('id') != entry_id]
        
        if len(entries) == original_count:
            error = f"Entry to delete not found in file storage: {entry_id}"
            current_app.logger.warning(error)
            return False, error
        
        if write_json_file(JOURNAL_FILE, entries):
            current_app.logger.info(f"Entry deleted from file storage: {entry_id}")
            return True, None
        else:
            error = "Failed to save after deletion to file storage"
            current_app.logger.error(f"{error}: {entry_id}")
            return False, error
            
    except Exception as e:
        error = f"Error deleting entry: {str(e)}"
        current_app.logger.error(error)
        return False, error


def get_entry_count():
    """Get the count of journal entries
    
    Returns:
        int: Number of entries
    """
    try:
        # If MongoDB is available, count from database
        if is_connected():
            collection = get_collection(JOURNAL_COLLECTION)
            count = collection.count_documents({})
            return count
        
        # Otherwise count from file
        entries = read_json_file(JOURNAL_FILE)
        return len(entries)
    except Exception as e:
        current_app.logger.error(f"Error counting entries: {str(e)}")
        return 0