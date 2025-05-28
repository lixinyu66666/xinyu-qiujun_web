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

# 确保上传目录存在
def ensure_upload_directory():
    """确保上传目录存在并可写入"""
    try:
        upload_dir = os.path.join(os.path.dirname(__file__), 'static/images')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir, exist_ok=True)
            print(f"创建上传目录: {upload_dir}")
        # 测试目录是否可写
        test_file = os.path.join(upload_dir, '.write_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        return True
    except Exception as e:
        print(f"警告：上传目录设置错误: {str(e)}")
        return False

# 应用启动时检查上传目录
ensure_upload_directory()

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
    """检查文件扩展名是否在允许的列表中
    
    增强版本：增加额外的验证和日志记录
    """
    if not filename or '.' not in filename:
        app.logger.warning(f"文件名无效或没有扩展名: {filename}")
        return False
        
    # 获取扩展名并转为小写
    ext = filename.rsplit('.', 1)[1].lower()
    
    # 检查扩展名是否在允许列表中
    is_allowed = ext in ALLOWED_EXTENSIONS
    
    if is_allowed:
        app.logger.info(f"文件类型被允许: {ext}")
    else:
        app.logger.warning(f"文件类型不被允许: {ext}")
        
    return is_allowed

def validate_image(stream):
    """验证图片格式并返回适当的文件扩展名
    
    增强版本：添加更多错误处理和格式支持
    """
    try:
        # 保存原始位置
        original_position = stream.tell()
        
        # 读取前512字节以检测文件类型
        header = stream.read(512)
        # 恢复文件指针位置
        stream.seek(original_position)
        
        # 使用imghdr识别格式
        format = imghdr.what(None, header)
        app.logger.info(f"图片格式检测结果: {format}")
        
        # 常见格式映射
        format_map = {
            'jpeg': '.jpg',
            'jpg': '.jpg',
            'png': '.png',
            'gif': '.gif',
            'bmp': '.bmp',
            'webp': '.webp'
        }
        
        if format and format in format_map:
            app.logger.info(f"使用imghdr检测到格式: {format}")
            return format_map[format]
        elif format:
            app.logger.info(f"使用imghdr检测到未映射格式: {format}")
            return f".{format}"
        
        # 如果imghdr识别失败，尝试基于header进行简单的标记检查
        if header.startswith(b'\xff\xd8'):
            app.logger.info("通过header检测到JPEG格式")
            return '.jpg'
        elif header.startswith(b'\x89PNG\r\n\x1a\n'):
            app.logger.info("通过header检测到PNG格式")
            return '.png'
        elif header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
            app.logger.info("通过header检测到GIF格式")
            return '.gif'
            
        # 最后的兜底方案：如果无法识别，记录头部字节
        app.logger.warning(f"无法识别的图片格式，头部十六进制: {header[:20].hex()}")
        return None
    except Exception as e:
        app.logger.error(f"验证图片格式时发生错误: {str(e)}", exc_info=True)
        # 尝试重置流指针
        try:
            stream.seek(original_position)
        except:
            pass
        return None

def check_file_size(file):
    """检查文件大小是否超过限制
    
    增强版本：增加异常处理，确保文件指针正确重置
    """
    try:
        # 保存当前文件指针位置
        current_pos = file.tell()
        
        # 移动到文件末尾获取大小
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        
        # 恢复原始文件指针位置
        file.seek(current_pos)
        
        app.logger.info(f"上传文件大小: {file_size/1024/1024:.2f}MB")
        
        # 确定大小限制
        size_limit = 4 * 1024 * 1024 if IS_VERCEL else 16 * 1024 * 1024
        limit_mb = 4 if IS_VERCEL else 16
        
        # 验证文件大小
        if file_size > size_limit:
            return False, f"文件大小 ({file_size/1024/1024:.1f}MB) 超过限制 ({limit_mb}MB)"
        
        return True, "文件大小合适"
    except Exception as e:
        app.logger.error(f"检查文件大小时出错: {str(e)}")
        try:
            # 尝试重置文件指针到开始位置
            file.seek(0)
        except:
            pass
        return False, f"无法验证文件大小: {str(e)}"

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
    app.logger.info("开始处理图片上传请求")
    if not session.get('logged_in'):
        app.logger.warning("未登录用户尝试上传图片")
        return redirect(url_for('login'))

    if 'image' not in request.files:
        app.logger.warning("上传请求中没有图片文件")
        flash('没有选择文件')
        return redirect(url_for('gallery'))
        
    file = request.files['image']
    app.logger.info(f"接收到文件上传: {file.filename}")
    
    if file.filename == '':
        app.logger.warning("上传的文件名为空")
        flash('没有选择文件')
        return redirect(url_for('gallery'))

    if not allowed_file(file.filename):
        app.logger.warning(f"不支持的文件类型: {file.filename}")
        flash('不支持的文件类型')
        return redirect(url_for('gallery'))
        
    # 检查文件大小
    size_ok, message = check_file_size(file)
    if not size_ok:
        app.logger.warning(f"图片太大: {message}")
        flash(f'图片太大: {message}')
        return redirect(url_for('gallery'))
        
    # 完全重写上传逻辑
    try:
        app.logger.info("开始处理文件保存流程")
        
        # 确保上传目录存在且可写入
        if not os.path.exists(UPLOAD_FOLDER):
            app.logger.info(f"创建上传目录: {UPLOAD_FOLDER}")
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # 测试目录是否可写
        try:
            test_file = os.path.join(UPLOAD_FOLDER, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            app.logger.info("上传目录可写入")
        except Exception as perm_err:
            app.logger.error(f"上传目录权限错误: {str(perm_err)}")
            flash('服务器配置错误: 上传目录不可写')
            return redirect(url_for('gallery'))
            
        # 获取现有图片列表
        try:
            images = [f for f in os.listdir(UPLOAD_FOLDER) 
                     if f != 'background.jpg' and any(f.endswith(ext) for ext in ALLOWED_EXTENSIONS)]
            next_number = len(images) + 1
            app.logger.info(f"下一个图片编号: {next_number}")
        except Exception as list_err:
            app.logger.error(f"获取图片列表出错: {str(list_err)}")
            next_number = 1 # 如果出错，默认从1开始
        
        # 确定文件扩展名
        original_ext = os.path.splitext(file.filename)[1].lower()
        
        # 如果原始扩展名不符合要求，尝试验证图片格式
        if original_ext not in ['.jpg', '.jpeg', '.png', '.gif', '.JPG', '.JPEG', '.PNG', '.GIF']:
            try:
                file_ext = validate_image(file.stream)
                if not file_ext:
                    app.logger.warning("无法验证图片格式且原始扩展名无效")
                    flash('无效的图片文件格式')
                    return redirect(url_for('gallery'))
            except Exception as fmt_err:
                app.logger.error(f"验证图片格式错误: {str(fmt_err)}")
                flash('无法验证图片格式')
                return redirect(url_for('gallery'))
        else:
            # 使用标准化的小写扩展名
            file_ext = original_ext.lower()
            app.logger.info(f"使用原始文件扩展名: {file_ext}")
            
        # 保存文件
        filename = f"{next_number:02d}{file_ext}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # 避免覆盖现有文件
        while os.path.exists(file_path):
            next_number += 1
            filename = f"{next_number:02d}{file_ext}"
            file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        app.logger.info(f"即将保存文件: {file_path}")
        
        # 使用更安全的文件保存方法
        try:
            # 创建临时文件
            temp_path = os.path.join(UPLOAD_FOLDER, f".temp_{filename}")
            
            # 保存到临时文件
            file.save(temp_path)
            app.logger.info(f"文件已保存到临时位置: {temp_path}")
            
            # 如果临时文件存在，则重命名为最终文件名
            if os.path.exists(temp_path):
                # 如果目标文件存在，先删除
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                # 重命名临时文件
                os.rename(temp_path, file_path)
                app.logger.info(f"临时文件已重命名为: {file_path}")
            else:
                raise Exception("临时文件未能创建")
        except Exception as save_err:
            app.logger.error(f"保存文件过程中出错: {str(save_err)}")
            # 清理可能留下的临时文件
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise save_err
        
        # 验证文件是否已成功保存
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            app.logger.info(f"图片上传成功: {filename}, 大小: {file_size/1024:.1f}KB")
            flash('图片上传成功')
        else:
            app.logger.error(f"文件保存失败: {file_path}")
            flash('图片上传失败: 保存失败')
            
        return redirect(url_for('gallery'))
    except Exception as e:
        app.logger.error(f"图片上传错误: {str(e)}", exc_info=True)
        flash('图片上传失败: 服务器处理错误')
        return redirect(url_for('gallery'))
            
        try:
            # 获取图片目录中的最后一个数字
            images = [f for f in os.listdir(UPLOAD_FOLDER) 
                    if f != 'background.jpg' and any(f.endswith(ext) for ext in ALLOWED_EXTENSIONS)]
            next_number = len(images) + 1
            
            # 确保上传目录存在
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                app.logger.info(f"创建上传文件夹: {UPLOAD_FOLDER}")
                
            # 根据文件内容确定扩展名
            try:
                file_ext = validate_image(file.stream)
                if not file_ext:
                    app.logger.warning("无法验证图片格式")
                    # 使用原始文件扩展名作为后备
                    original_ext = os.path.splitext(file.filename)[1].lower()
                    if original_ext in ['.jpg', '.jpeg', '.png', '.gif']:
                        file_ext = original_ext
                    else:
                        flash('无效的图片文件')
                        return redirect(url_for('gallery'))
            except Exception as img_err:
                app.logger.error(f"验证图片格式时出错: {str(img_err)}")
                # 使用原始文件扩展名
                file_ext = os.path.splitext(file.filename)[1].lower()
                
            # 构建新文件名
            filename = f"{next_number:02d}{file_ext}"
            
            # 保存文件
            target_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            app.logger.info(f"尝试保存文件到: {target_path}")
            file.save(target_path)
            
            # 验证文件是否已成功保存
            if os.path.exists(target_path):
                app.logger.info(f"图片上传成功: {filename}")
                flash('图片上传成功')
            else:
                app.logger.error(f"文件保存失败: {target_path}")
                flash('图片上传失败: 无法保存文件')
            
            return redirect(url_for('gallery'))
        except Exception as e:
            app.logger.error(f"图片上传错误: {str(e)}", exc_info=True)
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
    
    # 检查上传目录状态
    upload_dir_exists = os.path.exists(UPLOAD_FOLDER)
    upload_dir_writable = False
    if upload_dir_exists:
        try:
            test_file = os.path.join(UPLOAD_FOLDER, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            upload_dir_writable = True
        except:
            pass
    
    status = {
        'mongodb_connected': mongo_client is not None,
        'entries_count': len(load_journal()),
        'vercel': IS_VERCEL,
        'mongodb_uri_configured': MONGODB_URI is not None,
        'time': datetime.now(CHINA_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S'),
        'upload_folder': UPLOAD_FOLDER,
        'upload_folder_exists': upload_dir_exists,
        'upload_folder_writable': upload_dir_writable,
        'max_upload_size': app.config['MAX_CONTENT_LENGTH'] / (1024 * 1024)
    }
    
    return status

# Application instance for Vercel
application = app

# 添加一个测试上传的路由，便于调试
@app.route('/test_upload')
def test_upload():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    # 检查上传目录状态
    upload_dir_exists = os.path.exists(UPLOAD_FOLDER)
    upload_dir_writable = False
    if upload_dir_exists:
        try:
            test_file = os.path.join(UPLOAD_FOLDER, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            upload_dir_writable = True
        except Exception as e:
            app.logger.error(f"上传目录权限测试失败: {str(e)}")
    
    # 查找已有的图片文件
    images = []
    if os.path.exists(UPLOAD_FOLDER):
        for file in os.listdir(UPLOAD_FOLDER):
            if file != "background.jpg" and any(file.endswith(ext) for ext in ALLOWED_EXTENSIONS):
                file_path = os.path.join(UPLOAD_FOLDER, file)
                file_size = os.path.getsize(file_path)
                file_mode = oct(os.stat(file_path).st_mode)[-3:]
                images.append({
                    'name': file,
                    'size': f"{file_size/1024:.1f}KB",
                    'mode': file_mode,
                    'readable': os.access(file_path, os.R_OK),
                    'writable': os.access(file_path, os.W_OK)
                })
    
    # 返回HTML页面
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>上传测试</title>
        <style>
            body {{ font-family: Arial; padding: 20px; }}
            h1, h2 {{ color: #333; }}
            .good {{ color: green; }}
            .bad {{ color: red; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .form-container {{ margin: 20px 0; padding: 15px; background: #f9f9f9; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>图片上传测试页面</h1>
        
        <h2>系统状态</h2>
        <p>上传目录: {UPLOAD_FOLDER}</p>
        <p>目录存在: <span class="{'good' if upload_dir_exists else 'bad'}">{upload_dir_exists}</span></p>
        <p>目录可写: <span class="{'good' if upload_dir_writable else 'bad'}">{upload_dir_writable}</span></p>
        <p>最大上传大小: {app.config['MAX_CONTENT_LENGTH']/1024/1024}MB</p>
        
        <div class="form-container">
            <h2>测试上传</h2>
            <form action="{url_for('upload_image')}" method="post" enctype="multipart/form-data">
                <p>选择一张图片 (最大 {4 if IS_VERCEL else 16}MB):</p>
                <input type="file" name="image" accept="image/*"><br><br>
                <input type="submit" value="上传图片">
            </form>
        </div>
        
        <h2>现有图片 ({len(images)}个)</h2>
        <table>
            <tr>
                <th>文件名</th>
                <th>大小</th>
                <th>权限</th>
                <th>可读</th>
                <th>可写</th>
            </tr>
            {''.join(f'<tr><td>{img["name"]}</td><td>{img["size"]}</td><td>{img["mode"]}</td><td>{img["readable"]}</td><td>{img["writable"]}</td></tr>' for img in images)}
        </table>
        
        <p><a href="{url_for('gallery')}">返回相册</a></p>
    </body>
    </html>
    """
    return html

# 在文件末尾添加一个测试路由，用于检查MongoDB连接状态
@app.route('/test_db')
def test_db():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    result = {
        'status': '连接成功' if mongo_client else '未连接',
        'database': DB_NAME,
        'collection': COLLECTION_NAME
    }
    
    if mongo_client:
        try:
            # 尝试执行一个简单的操作确认连接
            mongo_client.server_info()
            result['ping'] = '成功'
        except Exception as e:
            result['ping'] = f'失败: {str(e)}'
    
    return result