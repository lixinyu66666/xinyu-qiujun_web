"""
Authentication routes.
This module handles user authentication routes such as login, logout, etc.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from config import PASSWORD

# Create blueprint
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login
    
    GET: Display login form
    POST: Process login credentials
    """
    if request.method == 'POST':
        if request.form['password'] == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('main.home'))
        return render_template('login.html', error='密码错误')
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Handle user logout"""
    session.pop('logged_in', None)
    flash('您已退出登录')
    return redirect(url_for('auth.login'))