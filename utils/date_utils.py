"""
Utility functions for date and time operations.
This module handles date formatting, calculations, and timezone conversions.
"""

from datetime import datetime, timedelta
import pytz
from config import CHINA_TIMEZONE, LOVE_START_DATE

def get_current_time():
    """Get current time in China timezone
    
    Returns:
        datetime: Current time in China timezone
    """
    return datetime.now(CHINA_TIMEZONE)

def format_date(date, format_str='%Y年%m月%d日'):
    """Format date to string using the specified format
    
    Args:
        date (datetime): Date to format
        format_str (str): Format string
        
    Returns:
        str: Formatted date string
    """
    return date.strftime(format_str)

def format_time(date, format_str='%H:%M:%S'):
    """Format time to string using the specified format
    
    Args:
        date (datetime): Date to format
        format_str (str): Format string
        
    Returns:
        str: Formatted time string
    """
    return date.strftime(format_str)

def get_days_together(start_date=LOVE_START_DATE, count_today=True):
    """Calculate days in relationship
    
    Args:
        start_date (datetime): Relationship start date
        count_today (bool): Whether to count today as a day
        
    Returns:
        int: Number of days in relationship
    """
    today = datetime.now(CHINA_TIMEZONE)
    days_together = (today - start_date).days
    
    if count_today:
        days_together += 1  # Adding 1 to include today
        
    return days_together

def get_next_milestone(start_date=LOVE_START_DATE):
    """Calculate the next milestone in relationship
    
    Args:
        start_date (datetime): Relationship start date
        
    Returns:
        tuple: (milestone_text, days_to_milestone)
    """
    today = datetime.now(CHINA_TIMEZONE)
    
    # Calculate days together (using actual days, without adding 1)
    days_together = (today - start_date).days
    
    # Calculate how many 100-day periods have passed
    hundreds_passed = days_together // 100
    
    # Calculate the date of the next 100-day milestone
    next_milestone = start_date + timedelta(days=(hundreds_passed + 1) * 100)
    
    # Calculate days to milestone
    days_to_milestone = (next_milestone - today).days
    
    # Format milestone text
    if hundreds_passed == 0:
        # Less than 100 days
        milestone_text = f"100天纪念日 ({format_date(next_milestone)})"
    else:
        # At least 100 days have passed
        next_hundred = hundreds_passed + 1
        milestone_text = f"{next_hundred * 100}天纪念日 ({format_date(next_milestone)})"
    
    return milestone_text, days_to_milestone