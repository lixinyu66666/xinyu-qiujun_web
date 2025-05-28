from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
import os
import json
from dotenv import load_dotenv
import imghdr
import pymongo
import sys
import pytz

# 定义中国时区常量
CHINA_TIMEZONE = pytz.timezone('Asia/Shanghai')

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))  # For session encryption

# 设置日志
import logging
from logging.handlers import RotatingFileHandler

# 确保日志目录存在
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
if not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir)
    except Exception as e:
        print(f"无法创建日志目录: {e}")

# 配置日志处理器
try:
    handler = RotatingFileHandler(os.path.join(log_dir, 'app.log'), maxBytes=10240, backupCount=5)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('应用启动')
except Exception as e:
    print(f"无法配置日志: {e}")

# Set password from environment variable
PASSWORD = os.getenv('PASSWORD') 
if not PASSWORD:
    print("WARNING: Password environment variable not set. Please ensure the PASSWORD environment variable is configured.")
    PASSWORD = "Please set password in .env file"  # This is just a placeholder

# Set relationship anniversary date
LOVE_START_DATE = datetime(2022, 12, 10, tzinfo=pytz.timezone('Asia/Shanghai'))  # 使用中国时区

# 判断是否在Vercel环境中运行
IS_VERCEL = os.environ.get('VERCEL') == '1'

# MongoDB 连接设置
MONGODB_URI = os.getenv('MONGODB_URI')
DB_NAME = os.getenv('MONGODB_DB', 'journal_db')
COLLECTION_NAME = 'entries'

# 初始化 MongoDB 客户端
mongo_client = None
db = None
collection = None

def init_mongodb_connection():
    global mongo_client, db, collection
    try:
        if MONGODB_URI:
            # 设置更短的连接超时时间，避免长时间等待
            mongo_client = pymongo.MongoClient(
                MONGODB_URI, 
                serverSelectionTimeoutMS=5000,  # 5秒超时
                connectTimeoutMS=5000,
                socketTimeoutMS=5000
            )
            # 验证连接是否成功
            mongo_client.server_info()  # 如果连接失败，这里会抛出异常
            
            db = mongo_client[DB_NAME]
            collection = db[COLLECTION_NAME]
            app.logger.info("MongoDB 连接成功")
            return True
        else:
            app.logger.warning("未配置MongoDB URI，将使用本地文件存储")
            return False
    except Exception as e:
        app.logger.error(f"MongoDB 连接错误: {e}")
        mongo_client = None
        db = None
        collection = None
        return False

# 尝试初始化MongoDB连接
init_mongodb_connection()

# 日志文件路径 - 在没有MongoDB或本地开发环境时使用
JOURNAL_FILE = os.path.join(os.path.dirname(__file__), 'data/journal.json')
if IS_VERCEL and not mongo_client:
    # Vercel上没有MongoDB时使用/tmp目录
    JOURNAL_FILE = '/tmp/journal.json'

# 文件上传配置
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static/images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'JPG', 'JPEG', 'PNG', 'GIF'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# 在Vercel环境下设置较小的大小限制，防止PAYLOAD_TOO_LARGE错误
if IS_VERCEL:
    app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024  # 4MB max file size for Vercel
else:
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size for local

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

def check_file_size(file):
    """检查文件大小是否超过限制"""
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    # 计算Vercel环境的大小限制
    vercel_limit = 4 * 1024 * 1024  # 4MB
    
    if IS_VERCEL and file_size > vercel_limit:
        return False, f"文件大小 ({file_size/1024/1024:.1f}MB) 超过Vercel的限制 (4MB)"
    
    return True, "文件大小合适"

def load_journal():
    """加载日志数据"""
    try:
        # 如果 MongoDB 可用，从数据库中加载
        if mongo_client:
            entries = list(collection.find({}, {'_id': 0}))  # 排除MongoDB的_id字段
            # 确保所有条目有正确的格式
            return sorted(entries, key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # 否则从本地文件加载
        if os.path.exists(JOURNAL_FILE):
            try:
                with open(JOURNAL_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                app.logger.error(f"加载日志文件错误: {e}")
                # 如果文件损坏或无法读取，返回空列表
                return []
        return []
    except Exception as e:
        app.logger.error(f"加载日志错误: {e}")
        return []

def save_journal(entries):
    """保存日志数据"""
    try:
        # 如果 MongoDB 可用，保存到数据库
        if mongo_client:
            # 检查MongoDB连接是否有效
            try:
                # 尝试Ping MongoDB服务器
                mongo_client.admin.command('ping')
                
                # 使用更安全的方法：对于每个条目，使用upsert操作
                # 这样如果操作失败，不会丢失所有数据
                for entry in entries:
                    # 使用id作为唯一标识
                    query = {'id': entry['id']}
                    # 使用upsert=True，存在则更新，不存在则插入
                    collection.update_one(query, {'$set': entry}, upsert=True)
                    
                app.logger.info(f"成功保存/更新 {len(entries)} 条日志到MongoDB")
                return True
            except Exception as e:
                app.logger.error(f"MongoDB连接或操作失败: {e}")
                # 如果MongoDB操作失败，回退到文件存储
        
        # MongoDB不可用或操作失败，保存到本地文件
        dir_path = os.path.dirname(JOURNAL_FILE)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            
        with open(JOURNAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        app.logger.error(f"保存日志错误: {e}")
        return False

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
    
    # Calculate days to milestone
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
    today = datetime.now(CHINA_TIMEZONE)
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
    today = datetime.now(CHINA_TIMEZONE)
    
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
    
    today = datetime.now(CHINA_TIMEZONE)
    
    return render_template('journal.html',
                         entries=entries,
                         current_year=today.year)

@app.route('/add_entry', methods=['GET', 'POST'])
def add_entry():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'GET':
        today = datetime.now(CHINA_TIMEZONE)
        return render_template('add_entry.html', current_year=today.year)
        
    # POST request handling
    try:
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        author = request.form.get('author', '').strip()
        
        if not all([title, content, author]):
            flash('请填写所有必填字段')
            return redirect(url_for('add_entry'))
        
        app.logger.info(f"尝试添加日志: {title} by {author}")
        
        now = datetime.now(CHINA_TIMEZONE)
        entry_id = str(int(now.timestamp()))
        entry = {
            'id': entry_id,
            'title': title,
            'content': content,
            'author': author,
            'date': now.strftime('%Y年%m月%d日'),
            'time': now.strftime('%H:%M:%S'),
            'timestamp': now.timestamp()
        }
        
        success = False
        
        # 如果MongoDB可用，尝试添加
        if mongo_client:
            try:
                # 检查连接是否有效
                mongo_client.admin.command('ping')
                
                # 直接插入
                result = collection.insert_one(entry)
                if result.inserted_id:
                    app.logger.info(f"日志已成功添加到MongoDB: {entry_id}")
                    success = True
                else:
                    app.logger.warning(f"MongoDB插入日志没有返回ID: {entry_id}")
            except Exception as mongo_err:
                app.logger.error(f"MongoDB添加日志失败: {mongo_err}")
                # MongoDB失败，将尝试文件存储
        
        # 如果MongoDB不可用或添加失败，使用文件存储
        if not success:
            try:
                entries = load_journal()
                entries.append(entry)
                success = save_journal(entries)
                if success:
                    app.logger.info(f"日志已添加到文件存储: {entry_id}")
                else:
                    app.logger.error(f"文件存储保存日志失败: {entry_id}")
            except Exception as file_err:
                app.logger.error(f"文件存储操作失败: {file_err}")
        
        if success:
            flash('日志添加成功')
        else:
            flash('保存日志时出错，请稍后重试')
            
        return redirect(url_for('journal'))
    except Exception as e:
        app.logger.error(f"添加日志出错: {str(e)}")
        flash(f'添加日志时发生错误，请联系管理员')
        return redirect(url_for('add_entry'))

@app.route('/edit/<id>')
def edit(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    entries = load_journal()
    for entry in entries:
        if entry['id'] == id:
            today = datetime.now(CHINA_TIMEZONE)
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
    
    try:
        entries = load_journal()
        entry_found = False
        
        for entry in entries:
            if entry['id'] == id:
                entry['title'] = title
                entry['content'] = content
                entry['author'] = author
                now = datetime.now(CHINA_TIMEZONE)
                entry['date'] = now.strftime('%Y年%m月%d日')
                entry['time'] = now.strftime('%H:%M:%S')
                entry['timestamp'] = now.timestamp()
                entry_found = True
                break
        
        if not entry_found:
            flash('找不到指定的日志')
            return redirect(url_for('journal'))
            
        if save_journal(entries):
            flash('日志已更新')
        else:
            flash('更新日志时出错，请稍后重试')
            
        return redirect(url_for('view_entry', id=id))
    except Exception as e:
        app.logger.error(f"更新日志出错: {str(e)}")
        flash('更新日志时发生错误，请联系管理员')
        return redirect(url_for('edit', id=id))

@app.route('/delete_entry', methods=['POST'])
def delete_entry():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    entry_id = request.form.get('entry_id')
    if not entry_id:
        return redirect(url_for('journal'))
    
    try:
        app.logger.info(f"尝试删除日志: {entry_id}")
        success = False
        
        # 如果MongoDB可用，尝试从数据库删除
        if mongo_client:
            try:
                result = collection.delete_one({'id': entry_id})
                if result.deleted_count > 0:
                    app.logger.info(f"日志已从MongoDB中删除: {entry_id}")
                    success = True
                else:
                    app.logger.warning(f"MongoDB中未找到要删除的日志: {entry_id}")
                    # MongoDB中没有找到，将尝试文件存储
            except Exception as mongo_err:
                app.logger.error(f"MongoDB删除日志失败: {mongo_err}")
                # MongoDB操作失败，将尝试文件存储
        
        # 如果MongoDB不可用或删除失败，使用文件存储
        if not success:
            entries = load_journal()
            original_count = len(entries)
            entries = [entry for entry in entries if entry['id'] != entry_id]
            
            if len(entries) == original_count:
                # 没有删除任何条目
                flash('找不到要删除的日志')
                app.logger.warning(f"在文件存储中未找到要删除的日志: {entry_id}")
                return redirect(url_for('journal'))
            
            if save_journal(entries):
                app.logger.info(f"日志已从文件存储中删除: {entry_id}")
                success = True
            else:
                app.logger.error(f"从文件存储删除日志失败: {entry_id}")
        
        if success:
            flash('日志已删除')
        else:
            flash('删除日志时出错，请稍后重试')
            
        return redirect(url_for('journal'))
    except Exception as e:
        app.logger.error(f"删除日志出错: {str(e)}")
        flash('删除日志时发生错误，请联系管理员')
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
        # 检查文件大小
        size_ok, message = check_file_size(file)
        if not size_ok:
            flash(f'图片太大: {message}')
            app.logger.warning(f"图片上传失败: {message}")
            return redirect(url_for('gallery'))
            
        try:
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
            flash('图片上传成功')
            app.logger.info(f"图片上传成功: {filename}")
            return redirect(url_for('gallery'))
        except Exception as e:
            app.logger.error(f"图片上传错误: {str(e)}")
            flash(f'图片上传失败: 服务器错误')
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
            today = datetime.now(CHINA_TIMEZONE)
            return render_template('view_entry.html', 
                                entry=entry,
                                current_year=today.year)
    
    flash('找不到指定的日志')
    return redirect(url_for('journal'))

# 添加一个简单的日志状态API，方便调试
@app.route('/api/status', methods=['GET'])
def api_status():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    status = {
        'mongodb_connected': mongo_client is not None,
        'entries_count': len(load_journal()),
        'vercel': IS_VERCEL,
        'mongodb_uri_configured': MONGODB_URI is not None,
        'time': datetime.now(CHINA_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return status

# Application instance for Vercel
application = app

# 在文件末尾添加一个测试路由，用于检查MongoDB连接状态

@app.route('/test_db')
def test_db():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    result = {
        'is_vercel': IS_VERCEL,
        'mongodb_uri_set': bool(MONGODB_URI),
        'mongo_client': bool(mongo_client),
        'connection_status': 'Unknown'
    }
    
    try:
        if mongo_client:
            # 尝试ping数据库服务器
            mongo_client.admin.command('ping')
            result['connection_status'] = 'Connected'
            
            # 尝试列出所有日志条目
            entries = list(collection.find({}, {'_id': 0}))
            result['entries_count'] = len(entries)
            result['entries'] = entries
            
            return f"<pre>{json.dumps(result, indent=2, ensure_ascii=False)}</pre>"
        else:
            result['connection_status'] = 'Not Connected'
            return f"<pre>{json.dumps(result, indent=2)}</pre>"
    except Exception as e:
        result['connection_status'] = f'Error: {str(e)}'
        return f"<pre>{json.dumps(result, indent=2)}</pre>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)