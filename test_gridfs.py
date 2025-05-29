#!/usr/bin/env python
"""
Test script to verify GridFS functionality.
"""

import os
from flask import Flask
import io
from utils.db import init_mongodb_connection, get_db
import gridfs
from dotenv import load_dotenv
from config import GRIDFS_COLLECTION

# Load environment variables
load_dotenv()

# Create test Flask app for context
app = Flask(__name__)

def test_gridfs_storage():
    """Test GridFS storage functions"""
    print("Starting GridFS test...")
    
    with app.app_context():
        # Initialize MongoDB connection
        init_result = init_mongodb_connection()
        print(f"MongoDB connection initialized: {init_result}")
        
        if not init_result:
            print("Failed to initialize MongoDB connection")
            return False
        
        # Get database
        db = get_db()
        # PyMongo Database objects don't support bool testing
        # Instead, use is_connected
        from utils.db import is_connected
        if not is_connected():
            print("Failed to get a valid database connection")
            return False
            
        # Create GridFS instance
        from gridfs.synchronous import GridFS
        fs = GridFS(db, collection=GRIDFS_COLLECTION)
        print(f"GridFS instance created for collection: {GRIDFS_COLLECTION}")
        
        # Create test file
        test_data = io.BytesIO(b"Hello, GridFS!")
        test_data.seek(0)
        
        # Upload to GridFS
        file_id = fs.put(test_data, filename="test.txt", content_type="text/plain")
        print(f"Uploaded test file with ID: {file_id}")
        
        # Find by ID
        file = fs.get(file_id)
        content = file.read().decode('utf-8')
        print(f"Retrieved file content: '{content}'")
        
        # Clean up - delete file
        fs.delete(file_id)
        print(f"Deleted test file with ID: {file_id}")
        
        print("GridFS test completed successfully!")
        return True

if __name__ == "__main__":
    success = test_gridfs_storage()
    if success:
        print("All tests passed!")
    else:
        print("Tests failed!")
