from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))  # 用于会话加密

# 设置密码（从环境变量读取，如果没有则使用默认值）
PASSWORD = os.getenv('PASSWORD', "620725")

# 设置恋爱纪念日期
LOVE_START_DATE = datetime(2022, 12, 9)  # 请根据实际日期调整

def get_image_files():
    # 获取imgs文件夹中的所有图片
    img_dir = os.path.join(os.path.dirname(__file__), 'static/images')
    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.JPG', '.JPEG', '.PNG', '.GIF'}
    images = []
    if os.path.exists(img_dir):
        for file in os.listdir(img_dir):
            if any(file.endswith(ext) for ext in valid_extensions):
                images.append(file)
    return sorted(images)  # 按文件名排序

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
        
    # 计算恋爱天数
    today = datetime.now()
    days_together = (today - LOVE_START_DATE).days
    
    # 获取所有图片
    images = get_image_files()
    
    return render_template('index.html', 
                         days_together=days_together,
                         images=images)

# Vercel需要的应用实例
application = app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True) 