from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
import os
import json
from dotenv import load_dotenv
import imghdr

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))  # For session encryption

# Set password from environment variable
PASSWORD = os.getenv('PASSWORD') 
if not PASSWORD:
    print("WARNING: Password environment variable not set. Please ensure the PASSWORD environment variable is configured.")
    PASSWORD = "Please set password in .env file"  # This is just a placeholder

# Set relationship anniversary date
LOVE_START_DATE = datetime(2022, 12, 10)  # Changed to December 10th

# 日志文件路径
JOURNAL_FILE = os.path.join(os.path.dirname(__file__), 'data/journal.json')

# 文件上传配置
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static/images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'JPG', 'JPEG', 'PNG', 'GIF'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image(stream):
    header = stream.read(512)
    stream.seek(0)
    format = imghdr.what(None, header)
    if not format:
        return None
    return '.' + (format if format != 'jpeg' else 'jpg')

def load_journal():
    """加载日志数据"""
    if os.path.exists(JOURNAL_FILE):
        with open(JOURNAL_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_journal(entries):
    """保存日志数据"""
    os.makedirs(os.path.dirname(JOURNAL_FILE), exist_ok=True)
    with open(JOURNAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

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
    # Calculate days together (using actual days, without adding 1)
    days_together = (today - start_date).days
    
    # Calculate how many 100-day periods have passed
    hundreds_passed = days_together // 100
    
    # Calculate the date of the next 100-day milestone
    next_milestone = start_date + timedelta(days=(hundreds_passed + 1) * 100)
    
    # Calculate days until the next milestone
    days_to_milestone = (next_milestone - today).days
    
    # Format milestone text
    if hundreds_passed == 0:
        # Less than 100 days
        milestone_text = f"100天纪念日 ({next_milestone.strftime('%Y年%m月%d日')})"
    else:
        # At least 100 days have passed
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
    
    return render_template('index.html', 
                         days_together=days_together,
                         today_date=today_date,
                         next_milestone=next_milestone,
                         days_to_milestone=days_to_milestone,
                         current_year=today.year)

@app.route('/gallery')
def gallery():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    images = get_image_files()
    today = datetime.now()
    
    return render_template('gallery.html',
                         images=images,
                         current_year=today.year)

@app.route('/journal')
def journal():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    entries = load_journal()
    sort = request.args.get('sort', 'newest')
    
    # 确保按创建时间排序日志条目
    if sort == 'oldest':
        entries.sort(key=lambda x: x['timestamp'])
    else:  # 默认为newest
        entries.sort(key=lambda x: x['timestamp'], reverse=True)
    
    today = datetime.now()
    
    return render_template('journal.html',
                         entries=entries,
                         current_year=today.year)

@app.route('/add_entry', methods=['GET', 'POST'])
def add_entry():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'GET':
        today = datetime.now()
        return render_template('add_entry.html', current_year=today.year)
        
    # POST request handling
    title = request.form.get('title')
    content = request.form.get('content')
    author = request.form.get('author')
    
    if not all([title, content, author]):
        flash('请填写所有必填字段')
        return redirect(url_for('journal'))
    
    now = datetime.now()
    entry = {
        'id': str(int(now.timestamp())),
        'title': title,
        'content': content,
        'author': author,
        'date': now.strftime('%Y年%m月%d日'),
        'time': now.strftime('%H:%M:%S'),
        'timestamp': now.timestamp()
    }
    
    entries = load_journal()
    entries.append(entry)
    save_journal(entries)
    
    return redirect(url_for('journal'))

@app.route('/edit/<id>')
def edit(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    entries = load_journal()
    for entry in entries:
        if entry['id'] == id:
            today = datetime.now()
            return render_template('edit_entry.html', 
                                entry=entry,
                                current_year=today.year)
    
    flash('找不到指定的日志')
    return redirect(url_for('journal'))

@app.route('/update/<id>', methods=['POST'])
def update_entry(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    title = request.form.get('title')
    content = request.form.get('content')
    author = request.form.get('author')
    
    if not all([title, content, author]):
        flash('请填写所有必填字段')
        return redirect(url_for('edit', id=id))
    
    entries = load_journal()
    for entry in entries:
        if entry['id'] == id:
            entry['title'] = title
            entry['content'] = content
            entry['author'] = author
            now = datetime.now()
            entry['date'] = now.strftime('%Y年%m月%d日')
            entry['time'] = now.strftime('%H:%M:%S')
            entry['timestamp'] = now.timestamp()
            break
    
    save_journal(entries)
    flash('日志已更新')
    return redirect(url_for('view_entry', id=id))

@app.route('/delete_entry', methods=['POST'])
def delete_entry():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    entry_id = request.form.get('entry_id')
    if not entry_id:
        return redirect(url_for('journal'))
    
    entries = load_journal()
    entries = [entry for entry in entries if entry['id'] != entry_id]
    save_journal(entries)
    
    return redirect(url_for('journal'))

@app.route('/upload', methods=['POST'])
def upload_image():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if 'image' not in request.files:
        flash('没有选择文件')
        return redirect(url_for('gallery'))
        
    file = request.files['image']
    if file.filename == '':
        flash('没有选择文件')
        return redirect(url_for('gallery'))

    if file and allowed_file(file.filename):
        # 获取图片目录中的最后一个数字
        images = [f for f in os.listdir(UPLOAD_FOLDER) 
                 if f != 'background.jpg' and any(f.endswith(ext) for ext in ALLOWED_EXTENSIONS)]
        next_number = len(images) + 1
        
        # 根据文件内容确定扩展名
        file_ext = validate_image(file.stream)
        if not file_ext:
            flash('无效的图片文件')
            return redirect(url_for('gallery'))
            
        # 构建新文件名
        filename = f"{next_number:02d}{file_ext}"
        
        # 保存文件
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return redirect(url_for('gallery'))
        
    flash('不支持的文件类型')
    return redirect(url_for('gallery'))

@app.route('/delete', methods=['POST'])
def delete_image():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    image = request.form.get('image')
    if not image:
        flash('未指定要删除的图片')
        return redirect(url_for('gallery'))
        
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image))
        # 重命名剩余文件以保持连续性
        rename_remaining_images()
        flash('图片已删除')
    except Exception as e:
        flash('删除图片时出错')
        
    return redirect(url_for('gallery'))

def rename_remaining_images():
    """重命名剩余的图片文件以保持连续的编号"""
    images = [f for f in os.listdir(UPLOAD_FOLDER) 
             if f != 'background.jpg' and any(f.endswith(ext) for ext in ALLOWED_EXTENSIONS)]
    images.sort()
    
    # 创建临时文件夹
    temp_dir = os.path.join(UPLOAD_FOLDER, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    # 先移动到临时文件夹
    for i, image in enumerate(images, 1):
        ext = os.path.splitext(image)[1]
        new_name = f"{i:02d}{ext}"
        old_path = os.path.join(UPLOAD_FOLDER, image)
        temp_path = os.path.join(temp_dir, new_name)
        os.rename(old_path, temp_path)
    
    # 再移回原目录
    for filename in os.listdir(temp_dir):
        old_path = os.path.join(temp_dir, filename)
        new_path = os.path.join(UPLOAD_FOLDER, filename)
        os.rename(old_path, new_path)
    
    # 删除临时文件夹
    os.rmdir(temp_dir)

@app.route('/view_entry/<id>')
def view_entry(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    entries = load_journal()
    for entry in entries:
        if entry['id'] == id:
            today = datetime.now()
            return render_template('view_entry.html', 
                                entry=entry,
                                current_year=today.year)
    
    flash('找不到指定的日志')
    return redirect(url_for('journal'))

# Application instance for Vercel
application = app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)