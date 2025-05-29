"""
API routes module.
This module handles API endpoints for the application.
"""

from flask import Blueprint, jsonify, redirect, url_for, session
from datetime import datetime
from utils.db import is_connected
from models.journal import get_entry_count
from utils.date_utils import get_current_time
from config import MONGODB_URI, IS_VERCEL

# Create blueprint
api_bp = Blueprint('api', __name__)


@api_bp.route('/status', methods=['GET'])
def status():
    """API endpoint for application status
    
    Returns system status information
    """
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))
    
    # Get current time
    now = get_current_time()
    
    # Get entry count
    entries_count = get_entry_count()
    
    # Build status object
    status_data = {
        'mongodb_connected': is_connected(),
        'entries_count': entries_count,
        'vercel': IS_VERCEL,
        'mongodb_uri_configured': MONGODB_URI is not None,
        'time': now.strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'ok'
    }
    
    return jsonify(status_data)


@api_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint
    
    Simple endpoint to check if the application is running
    """
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat()
    })


@api_bp.route('/test_db', methods=['GET'])
def test_db():
    """Test database connection
    
    Returns detailed information about database connection
    """
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))
    
    result = {
        'is_vercel': IS_VERCEL,
        'mongodb_uri_set': bool(MONGODB_URI),
        'connection_status': 'Unknown'
    }
    
    if is_connected():
        result['connection_status'] = 'Connected'
        result['entries_count'] = get_entry_count()
    else:
        result['connection_status'] = 'Not Connected'
    
    return jsonify(result)