from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
import os
import json
from dotenv import load_dotenv
import imghdr
import pymongo
import sys
import pytz

# Define China timezone constant
CHINA_TIMEZONE = pytz.timezone('Asia/Shanghai')

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))  # For session encryption

# Set up logging
import logging
from logging.handlers import RotatingFileHandler

# Ensure log directory exists
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
if not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir)
    except Exception as e:
        print(f"Unable to create log directory: {e}")

# Configure log handler
try:
    handler = RotatingFileHandler(os.path.join(log_dir, 'app.log'), maxBytes=10240, backupCount=5)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Application started')
except Exception as e:
    print(f"Unable to configure logging: {e}")

# Set password from environment variable
PASSWORD = os.getenv('PASSWORD') 
if not PASSWORD:
    print("WARNING: Password environment variable not set. Please ensure the PASSWORD environment variable is configured.")
    PASSWORD = "Please set password in .env file"  # This is just a placeholder

# Set relationship anniversary date
LOVE_START_DATE = datetime(2022, 12, 10, tzinfo=pytz.timezone('Asia/Shanghai'))  # Using China timezone

# Check if running in Vercel environment
IS_VERCEL = os.environ.get('VERCEL') == '1'

# Ensure upload directory exists and is writable
def ensure_upload_directory():
    """Ensure the upload directory exists and is writable
    
    Handle permission issues in Vercel environment
    """
    global UPLOAD_FOLDER
    try:
        # Initialize standard upload directory
        upload_dir = os.path.join(os.path.dirname(__file__), 'static/images')
        
        # Check if running in Vercel environment
        if IS_VERCEL:
            print("Detected Vercel environment, may need to use temporary upload directory")
            
            # Switch directly to /tmp directory, as static/images is usually read-only in Vercel
            upload_dir = '/tmp/images'
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir, exist_ok=True)
                
            # Test temporary directory
            test_file = os.path.join(upload_dir, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            print(f"Temporary upload directory set: {upload_dir}")
        else:
            # Non-Vercel environment: ensure directory exists
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir, exist_ok=True)
                
            # Test if directory is writable
            test_file = os.path.join(upload_dir, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        
        # Update global UPLOAD_FOLDER variable
        UPLOAD_FOLDER = upload_dir
        return True
    except Exception as e:
        print(f"Warning: Upload directory setup error: {str(e)}")
        return False

# MongoDB connection settings
MONGODB_URI = os.getenv('MONGODB_URI')
DB_NAME = os.getenv('MONGODB_DB', 'journal_db')
COLLECTION_NAME = 'entries'

# Initialize MongoDB client
mongo_client = None
db = None
collection = None

def init_mongodb_connection():
    global mongo_client, db, collection
    try:
        if MONGODB_URI:
            # Set shorter connection timeout to avoid long waits
            mongo_client = pymongo.MongoClient(
                MONGODB_URI, 
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=5000,
                socketTimeoutMS=5000
            )
            # Verify connection success
            mongo_client.server_info()  # This will throw an exception if connection fails
            
            db = mongo_client[DB_NAME]
            collection = db[COLLECTION_NAME]
            app.logger.info("MongoDB connection successful")
            return True
        else:
            app.logger.warning("MongoDB URI not configured, will use local file storage")
            return False
    except Exception as e:
        app.logger.error(f"MongoDB connection error: {e}")
        mongo_client = None
        db = None
        collection = None
        return False

# Attempt to initialize MongoDB connection
init_mongodb_connection()

# Journal file path - used when MongoDB is not available or in local development
JOURNAL_FILE = os.path.join(os.path.dirname(__file__), 'data/journal.json')
if IS_VERCEL and not mongo_client:
    # Use /tmp directory on Vercel when MongoDB is not available
    JOURNAL_FILE = '/tmp/journal.json'

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static/images')
# Check and ensure upload directory is writable at application startup
ensure_upload_directory()
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'JPG', 'JPEG', 'PNG', 'GIF'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Set smaller size limit in Vercel environment to prevent PAYLOAD_TOO_LARGE errors
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
    """Check if file size exceeds the limit"""
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    # Calculate size limit for Vercel environment
    vercel_limit = 4 * 1024 * 1024  # 4MB
    
    if IS_VERCEL and file_size > vercel_limit:
        return False, f"File size ({file_size/1024/1024:.1f}MB) exceeds Vercel limit (4MB)"
    
    return True, "File size is appropriate"

def load_journal():
    """Load journal data"""
    try:
        # If MongoDB is available, load from database
        if mongo_client:
            entries = list(collection.find({}, {'_id': 0}))  # Exclude MongoDB _id field
            # Ensure all entries have the correct format
            return sorted(entries, key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # Otherwise load from local file
        if os.path.exists(JOURNAL_FILE):
            try:
                with open(JOURNAL_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                app.logger.error(f"Error loading journal file: {e}")
                # If file is corrupted or unreadable, return empty list
                return []
        return []
    except Exception as e:
        app.logger.error(f"Error loading journal: {e}")
        return []

def save_journal(entries):
    """Save journal data"""
    try:
        # If MongoDB is available, save to database
        if mongo_client:
            # Check if MongoDB connection is valid
            try:
                # Try to ping MongoDB server
                mongo_client.admin.command('ping')
                
                # Use safer method: for each entry, use upsert operation
                # This way if operation fails, not all data will be lost
                for entry in entries:
                    # Use id as unique identifier
                    query = {'id': entry['id']}
                    # Use upsert=True to update if exists, insert if not
                    collection.update_one(query, {'$set': entry}, upsert=True)
                    
                app.logger.info(f"Successfully saved/updated {len(entries)} entries to MongoDB")
                return True
            except Exception as e:
                app.logger.error(f"MongoDB connection or operation failed: {e}")
                # If MongoDB operation fails, fall back to file storage
        
        # MongoDB unavailable or operation failed, save to local file
        dir_path = os.path.dirname(JOURNAL_FILE)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            
        with open(JOURNAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        app.logger.error(f"Error saving journal: {e}")
        return False

def get_image_files():
    """Get list of image files, supporting temporary directory
    
    Support loading images from temporary directory in Vercel environment
    """
    # Use current UPLOAD_FOLDER variable, which might be /tmp/images or static/images
    images = []
    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.JPG', '.JPEG', '.PNG', '.GIF'}
    
    try:
        # Get images from the actual upload directory
        for file in os.listdir(UPLOAD_FOLDER):
            if file == "background.jpg" or file.startswith('.'):
                continue
                
            if any(file.endswith(ext) for ext in ALLOWED_EXTENSIONS):
                if file not in images:
                    images.append(file)
    except Exception as e:
        app.logger.error(f"Unable to read upload directory: {str(e)}")
        
    # If using temporary directory and no images found, try reading from standard static directory
    if len(images) == 0 and '/tmp/' in UPLOAD_FOLDER:
        std_img_dir = os.path.join(os.path.dirname(__file__), 'static/images')
        try:
            for file in os.listdir(std_img_dir):
                if file == "background.jpg" or file.startswith('.'):
                    continue
                    
                if any(file.endswith(ext) for ext in ALLOWED_EXTENSIONS):
                    if file not in images:
                        images.append(file)
        except Exception as e:
            app.logger.error(f"Unable to read static images directory: {str(e)}")
    
    return sorted(images)
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
    
    # Ensure journal entries are sorted by creation time
    if sort == 'oldest':
        entries.sort(key=lambda x: x['timestamp'])
    else:  # default to newest
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
        
        app.logger.info(f"Attempting to add entry: {title} by {author}")
        
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
                    app.logger.info(f"Entry successfully added to MongoDB: {entry_id}")
                    success = True
                else:
                    app.logger.warning(f"MongoDB insert entry did not return ID: {entry_id}")
            except Exception as mongo_err:
                app.logger.error(f"MongoDB add entry failed: {mongo_err}")
                # MongoDB failed, will try file storage
        
        # If MongoDB is unavailable or add failed, use file storage
        if not success:
            try:
                entries = load_journal()
                entries.append(entry)
                success = save_journal(entries)
                if success:
                    app.logger.info(f"Entry added to file storage: {entry_id}")
                else:
                    app.logger.error(f"File storage save entry failed: {entry_id}")
            except Exception as file_err:
                app.logger.error(f"File storage operation failed: {file_err}")
        
        if success:
            flash('日志添加成功')
        else:
            flash('保存日志时出错，请稍后重试')
            
        return redirect(url_for('journal'))
    except Exception as e:
        app.logger.error(f"Error adding entry: {str(e)}")
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
        app.logger.error(f"Error updating entry: {str(e)}")
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
        app.logger.info(f"Attempting to delete entry: {entry_id}")
        success = False
        
        # 如果MongoDB可用，尝试从数据库删除
        if mongo_client:
            try:
                result = collection.delete_one({'id': entry_id})
                if result.deleted_count > 0:
                    app.logger.info(f"Entry successfully deleted from MongoDB: {entry_id}")
                    success = True
                else:
                    app.logger.warning(f"Entry to be deleted not found in MongoDB: {entry_id}")
                    # Not found in MongoDB, will try file storage
            except Exception as mongo_err:
                app.logger.error(f"MongoDB delete entry failed: {mongo_err}")
                # MongoDB operation failed, will try file storage
        
        # 如果MongoDB不可用或删除失败，使用文件存储
        if not success:
            entries = load_journal()
            original_count = len(entries)
            entries = [entry for entry in entries if entry['id'] != entry_id]
            
            if len(entries) == original_count:
                # No entries were deleted
                flash('找不到要删除的日志')
                app.logger.warning(f"Entry to be deleted not found in file storage: {entry_id}")
                return redirect(url_for('journal'))
            
            if save_journal(entries):
                app.logger.info(f"Entry successfully deleted from file storage: {entry_id}")
                success = True
            else:
                app.logger.error(f"Failed to delete entry from file storage: {entry_id}")
        
        if success:
            flash('日志已删除')
        else:
            flash('删除日志时出错，请稍后重试')
            
        return redirect(url_for('journal'))
    except Exception as e:
        app.logger.error(f"Error deleting entry: {str(e)}")
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

    if file and allowed_file(file.filename):            # Check file size
        size_ok, message = check_file_size(file)
        if not size_ok:
            flash(f'图片太大: {message}')
            app.logger.warning(f"Image upload failed: {message}")
            return redirect(url_for('gallery'))
            
        try:
            # Ensure upload directory exists and is writable again
            if not ensure_upload_directory():
                app.logger.error("Upload directory not writable, cannot continue upload")
                flash('服务器配置错误: 上传目录不可写')
                return redirect(url_for('gallery'))
            
            # Get the last number in the image directory
            try:
                images = [f for f in os.listdir(UPLOAD_FOLDER) 
                        if f != 'background.jpg' and any(f.endswith(ext) for ext in ALLOWED_EXTENSIONS)]
                next_number = len(images) + 1
            except Exception as dir_err:
                app.logger.error(f"Unable to get image list: {str(dir_err)}")
                next_number = 1  # If list cannot be obtained, start from 1
            
            # Determine extension based on file content
            file_ext = validate_image(file.stream)
            if not file_ext:
                flash('无效的图片文件')
                return redirect(url_for('gallery'))
                
            # Build new filename
            filename = f"{next_number:02d}{file_ext}"
            
            # Write to temporary file first, then rename
            target_path = os.path.join(UPLOAD_FOLDER, filename)
            temp_path = os.path.join(UPLOAD_FOLDER, f".temp_{filename}")
            
            app.logger.info(f"Attempting to save file to: {target_path}")
            file.save(temp_path)
            
            # If temporary file exists, rename to final filename
            if os.path.exists(temp_path):
                os.rename(temp_path, target_path)
                app.logger.info(f"Image upload successful: {filename}")
                
                # If using temporary directory in Vercel environment, try copying to static directory
                if IS_VERCEL and '/tmp/' in UPLOAD_FOLDER:
                    try:
                        static_dir = os.path.join(os.path.dirname(__file__), 'static/images')
                        if not os.path.exists(static_dir):
                            os.makedirs(static_dir, exist_ok=True)
                            
                        static_path = os.path.join(static_dir, filename)
                        
                        # Copy file to static directory
                        with open(target_path, 'rb') as src_file:
                            with open(static_path, 'wb') as dst_file:
                                dst_file.write(src_file.read())
                                
                        app.logger.info(f"Image copied to static directory: {static_path}")
                    except Exception as copy_err:
                        app.logger.error(f"Copy to static directory failed (does not affect upload): {str(copy_err)}")
                
                flash('图片上传成功')
            else:
                app.logger.error(f"Temporary file could not be created: {temp_path}")
                flash('图片上传失败: 无法保存文件')
                
            return redirect(url_for('gallery'))
        except Exception as e:
            app.logger.error(f"Image upload error: {str(e)}")
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
        # 尝试从当前上传目录删除文件
        file_path = os.path.join(UPLOAD_FOLDER, image)
        if os.path.exists(file_path):
            os.remove(file_path)
            app.logger.info(f"已从上传目录删除图片: {file_path}")
            
        # 如果是临时目录，同时检查原始静态目录
        if '/tmp/' in UPLOAD_FOLDER:
            std_path = os.path.join(os.path.dirname(__file__), 'static/images', image)
            if os.path.exists(std_path):
                try:
                    os.remove(std_path)
                    app.logger.info(f"已从静态目录删除图片: {std_path}")
                except Exception as std_err:
                    app.logger.error(f"删除静态目录图片失败: {str(std_err)}")
                    
        # 重命名剩余文件以保持连续性
        rename_remaining_images()
        flash('图片已删除')
    except Exception as e:
        app.logger.error(f"删除图片出错: {str(e)}")
        flash('删除图片时出错')
        
    return redirect(url_for('gallery'))

def rename_remaining_images():
    """Rename remaining image files to maintain sequential numbering"""
    images = [f for f in os.listdir(UPLOAD_FOLDER) 
             if f != 'background.jpg' and any(f.endswith(ext) for ext in ALLOWED_EXTENSIONS)]
    images.sort()
    
    # Create temporary folder
    temp_dir = os.path.join(UPLOAD_FOLDER, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    # First move to temporary folder
    for i, image in enumerate(images, 1):
        ext = os.path.splitext(image)[1]
        new_name = f"{i:02d}{ext}"
        old_path = os.path.join(UPLOAD_FOLDER, image)
        temp_path = os.path.join(temp_dir, new_name)
        os.rename(old_path, temp_path)
    
    # Then move back to original directory
    for filename in os.listdir(temp_dir):
        old_path = os.path.join(temp_dir, filename)
        new_path = os.path.join(UPLOAD_FOLDER, filename)
        os.rename(old_path, new_path)
    
    # Delete temporary folder
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

# Add a simple journal status API for debugging
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

# Add a test route at the end of the file to check MongoDB connection status

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
            # Try to ping database server
            mongo_client.admin.command('ping')
            result['connection_status'] = 'Connected'
            
            # Try to list all journal entries
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