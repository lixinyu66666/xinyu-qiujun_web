from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))  # For session encryption

# Set password (from environment variable or default value)
PASSWORD = os.getenv('PASSWORD', "620725")

# Set relationship anniversary date
LOVE_START_DATE = datetime(2022, 12, 9)  # Adjust to actual date

def get_image_files():
    # Get all images from the images directory
    img_dir = os.path.join(os.path.dirname(__file__), 'static/images')
    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.JPG', '.JPEG', '.PNG', '.GIF'}
    images = []
    if os.path.exists(img_dir):
        for file in os.listdir(img_dir):
            if any(file.endswith(ext) for ext in valid_extensions):
                images.append(file)
    return sorted(images)  # Sort by filename

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['password'] == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('home'))
        return render_template('login.html', error='密码错误')
    return render_template('login.html')

@app.route('/')
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    # Calculate days in relationship
    today = datetime.now()
    days_together = (today - LOVE_START_DATE).days
    
    # Get all images
    images = get_image_files()
    
    return render_template('index.html', 
                         days_together=days_together,
                         images=images)

# Application instance for Vercel
application = app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True) 