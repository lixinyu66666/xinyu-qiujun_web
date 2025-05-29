import pymongo
import logging
from flask import current_app
from config import MONGODB_URI, DB_NAME, JOURNAL_COLLECTION

# MongoDB global variables
mongo_client = None
db = None
collections = {}

def init_mongodb_connection():
    """Initialize MongoDB connection"""
    global mongo_client, db, collections
    try:
        if MONGODB_URI:
            # Set shorter connection timeout to avoid long waits
            mongo_client = pymongo.MongoClient(
                MONGODB_URI, 
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000
            )
            # Verify connection success
            mongo_client.server_info()
            
            db = mongo_client[DB_NAME]
            # Initialize journal collection
            collections[JOURNAL_COLLECTION] = db[JOURNAL_COLLECTION]
            
            try:
                current_app.logger.info("MongoDB connection successful")
            except RuntimeError:
                # If outside of app context, use regular logging
                logging.info("MongoDB connection successful")
            return True
        else:
            try:
                current_app.logger.warning("MongoDB URI not configured, will use local file storage")
            except RuntimeError:
                logging.warning("MongoDB URI not configured, will use local file storage")
            return False
    except Exception as e:
        try:
            current_app.logger.error(f"MongoDB connection error: {e}")
        except RuntimeError:
            logging.error(f"MongoDB connection error: {e}")
        mongo_client = None
        db = None
        collections = {}
        return False

def is_connected():
    """Check if MongoDB is connected"""
    global mongo_client
    if not mongo_client:
        return False
    try:
        # Try to ping database server
        mongo_client.admin.command('ping')
        return True
    except:
        return False

def get_collection(collection_name=JOURNAL_COLLECTION):
    """Get MongoDB collection
    
    Args:
        collection_name: Name of collection to retrieve (defaults to journal collection)
    
    Returns:
        MongoDB collection object or None if not connected
    """
    global collections
    return collections.get(collection_name)