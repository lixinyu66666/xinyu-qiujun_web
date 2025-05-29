"""
Main routes module.
This module handles main page routes such as home page, etc.
"""

from flask import Blueprint, render_template, redirect, url_for, session
from datetime import datetime
from utils.date_utils import get_current_time, get_days_together, get_next_milestone
from config import LOVE_START_DATE

# Create blueprint
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def home():
    """Display the home page with relationship statistics"""
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))
    
    # Get current time in China timezone
    today = get_current_time()
    
    # Calculate days in relationship (including today)
    days_together = get_days_together(LOVE_START_DATE, True)
    
    # Format today's date
    today_date = today.strftime("%Y年%m月%d日")
    
    # Get next milestone
    next_milestone, days_to_milestone = get_next_milestone(LOVE_START_DATE)
    
    return render_template('index.html', 
                         days_together=days_together,
                         today_date=today_date,
                         next_milestone=next_milestone,
                         days_to_milestone=days_to_milestone,
                         current_year=today.year)