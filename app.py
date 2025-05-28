from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))  # For session encryption

# Set password (from environment variable or default value)
PASSWORD = os.getenv('PASSWORD', "620725")

# Set relationship anniversary date
LOVE_START_DATE = datetime(2022, 12, 10)  # Changed to December 10th

def get_image_files():
    # Get all images from the images directory
    img_dir = os.path.join(os.path.dirname(__file__), 'static/images')
    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.JPG', '.JPEG', '.PNG', '.GIF'}
    images = []
    if os.path.exists(img_dir):
        for file in os.listdir(img_dir):
            if file != "background.jpg" and any(file.endswith(ext) for ext in valid_extensions):
                images.append(file)
    return sorted(images)  # Sort by filename

def get_next_milestone(start_date, today):
    # 计算已经开始的天数（这里使用实际天数，不加1）
    days_together = (today - start_date).days
    
    # 计算已经过了几个100天
    hundreds_passed = days_together // 100
    
    # 计算下一个100天纪念日的日期
    next_milestone = start_date + timedelta(days=(hundreds_passed + 1) * 100)
    
    # 计算距离下一个纪念日的天数
    days_to_milestone = (next_milestone - today).days
    
    # 格式化纪念日文本
    if hundreds_passed == 0:
        # 还不到100天
        milestone_text = f"100天纪念日 ({next_milestone.strftime('%Y年%m月%d日')})"
    else:
        # 已经过了至少100天
        next_hundred = hundreds_passed + 1
        milestone_text = f"{next_hundred * 100}天纪念日 ({next_milestone.strftime('%Y年%m月%d日')})"
    
    return milestone_text, days_to_milestone

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
    days_together = (today - LOVE_START_DATE).days + 1  # Adding 1 day to make it 901 days
    
    # Format today's date
    today_date = today.strftime("%Y年%m月%d日")
    
    # Get next milestone
    next_milestone, days_to_milestone = get_next_milestone(LOVE_START_DATE, today)
    
    # Get all images
    images = get_image_files()
    
    return render_template('index.html', 
                         days_together=days_together,
                         today_date=today_date,
                         next_milestone=next_milestone,
                         days_to_milestone=days_to_milestone,
                         images=images,
                         current_year=today.year)

# Application instance for Vercel
application = app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True) 