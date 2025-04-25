import os
import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import hashlib
import random
from datetime import datetime
from functools import wraps
import json
from typing import Dict, Any, List

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-testing')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///puzzle_data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# Define database models
class DataEntry(db.Model):
    __tablename__ = 'data_entries'

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(10), nullable=False)
    content_hash = db.Column(db.String(32), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ApiKey(db.Model):
    __tablename__ = 'api_keys'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime)

    @staticmethod
    def generate_key():
        """Generate a random API key"""
        return hashlib.sha256(os.urandom(32)).hexdigest()

    # For backward compatibility
    @property
    def content(self):
        if self.category == 'idiom':
            return f"{self.question} - {self.answer}"
        return f"{self.question} {self.answer}"

    def __repr__(self):
        return f'<DataEntry {self.id}: {self.category}>'

    @staticmethod
    def generate_hash(question, answer):
        """Generate MD5 hash for question and answer to ensure uniqueness"""
        combined = f"{question}|{answer}"
        return hashlib.md5(combined.encode()).hexdigest()

# Ensure data directory exists and database file is created
db_uri = app.config['SQLALCHEMY_DATABASE_URI']
if db_uri.startswith('sqlite:///'):
    db_path = db_uri.replace('sqlite:///', '')
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.getcwd(), db_path)

    # Create directory if it doesn't exist
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
        print(f"Created directory: {db_dir}")

    # Remove empty database file if it exists but has zero size
    if os.path.exists(db_path) and os.path.getsize(db_path) == 0:
        try:
            os.remove(db_path)
            print(f"Removed empty database file: {db_path}")
        except Exception as e:
            print(f"Error removing empty database file: {e}")

    # Create a new database file using direct SQLite connection if it doesn't exist
    if not os.path.exists(db_path):
        try:
            # Create an empty SQLite database file
            conn = sqlite3.connect(db_path)
            conn.close()
            print(f"Created new SQLite database file: {db_path}")
        except Exception as e:
            print(f"Error creating SQLite database file: {e}")

# Initialize database within app context
with app.app_context():
    try:
        # Create all tables
        db.create_all()
        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {e}")

# Context processor to make datetime available in all templates
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# Decorators for access control

# Helper function to check if request is from localhost
def is_local_request():
    """Check if the request is coming from localhost/local network

    根据config.py中的LOCAL_NETWORK_IPS配置检查请求IP是否在允许的本地网络范围内
    支持精确匹配和正则表达式模式匹配
    """
    from config import LOCAL_NETWORK_IPS
    import re

    client_ip = request.remote_addr

    # 检查IP是否在允许列表中
    for ip_pattern in LOCAL_NETWORK_IPS:
        # 如果是精确匹配
        if client_ip == ip_pattern:
            return True
        # 如果是正则表达式模式
        try:
            if re.match(ip_pattern, client_ip):
                return True
        except re.error:
            # 如果正则表达式无效，则跳过该模式
            continue

    return False

# API Key verification decorator for API endpoints
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if request is coming from localhost/local network
        if is_local_request():
            # Skip API key verification for local network requests
            return f(*args, **kwargs)

        # For non-local requests, require API key
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')

        if not api_key:
            return jsonify({'error': 'API key is required'}), 401

        # Check if API key exists and is active
        key = ApiKey.query.filter_by(key=api_key, is_active=True).first()
        if not key:
            return jsonify({'error': 'Invalid or inactive API key'}), 401

        # Update last used timestamp
        key.last_used_at = datetime.utcnow()
        db.session.commit()

        return f(*args, **kwargs)
    return decorated_function

# Local access only decorator for admin/management routes
def local_access_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if request is coming from localhost
        if not is_local_request():
            abort(403, description="Access denied. This page is only accessible from localhost.")
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
@local_access_only
def index():
    return render_template('index.html')

# API Routes
@app.route('/api/random/<int:count>', methods=['GET'])
@require_api_key
def get_random_entries(count):
    category = request.args.get('category')

    query = DataEntry.query
    if category:
        query = query.filter_by(category=category)

    # Get total count of matching entries
    total_entries = query.count()

    # If requested count is more than available, return all available
    if count > total_entries:
        count = total_entries

    # Get random entries
    if total_entries > 0:
        # SQLite-specific random ordering
        random_entries = query.order_by(db.func.random()).limit(count).all()

        result = [{
            'id': entry.id,
            'question': entry.question,
            'answer': entry.answer,
            'category': entry.category,
            'created_at': entry.created_at.isoformat()
        } for entry in random_entries]

        return jsonify(result)
    else:
        return jsonify([])

@app.route('/api/add', methods=['POST'])
@require_api_key
def add_entry():
    data = request.get_json()

    # Check for new format (question/answer)
    if data and 'question' in data and 'answer' in data and 'category' in data:
        question = data['question'].strip()
        answer = data['answer'].strip()
        category = data['category'].lower()

        # Validate fields
        if not question or not answer:
            return jsonify({'error': 'Question and answer cannot be empty'}), 400
    # Check for old format (content)
    elif data and 'content' in data and 'category' in data:
        content = data['content'].strip()
        category = data['category'].lower()

        # Validate content
        if not content:
            return jsonify({'error': 'Content cannot be empty'}), 400

        # Split content into question and answer based on category
        if category == 'riddle' or category == 'joke':
            # For riddles and jokes, try to split at the question mark
            parts = content.split('?', 1)
            if len(parts) > 1:
                question = parts[0].strip() + '?'
                answer = parts[1].strip()
            else:
                # If no question mark, use the whole content as question
                question = content
                answer = "No answer provided"
        elif category == 'idiom':
            # For idioms, split at the dash
            parts = content.split('-', 1)
            if len(parts) > 1:
                question = parts[0].strip()
                answer = parts[1].strip()
            else:
                # If no dash, use the whole content as question
                question = content
                answer = "No meaning provided"
        else:
            question = content
            answer = ""
    else:
        return jsonify({'error': 'Missing required fields'}), 400

    # Validate category
    if category not in ['riddle', 'joke', 'idiom']:
        return jsonify({'error': 'Invalid category. Must be one of: riddle, joke, idiom'}), 400

    # Generate hash for deduplication
    content_hash = DataEntry.generate_hash(question, answer)

    # Check if entry already exists
    existing_entry = DataEntry.query.filter_by(content_hash=content_hash).first()
    if existing_entry:
        return jsonify({'error': 'This entry already exists in the database'}), 409

    # Create new entry
    new_entry = DataEntry(
        question=question,
        answer=answer,
        category=category,
        content_hash=content_hash
    )

    try:
        db.session.add(new_entry)
        db.session.commit()
        return jsonify({
            'id': new_entry.id,
            'question': new_entry.question,
            'answer': new_entry.answer,
            'category': new_entry.category,
            'created_at': new_entry.created_at.isoformat()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to add entry: {str(e)}'}), 500

@app.route('/browse')
@local_access_only
def browse():
    category = request.args.get('category')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = DataEntry.query
    if category:
        query = query.filter_by(category=category)

    pagination = query.order_by(DataEntry.created_at.desc()).paginate(page=page, per_page=per_page)
    entries = pagination.items

    return render_template('browse.html', entries=entries, pagination=pagination, category=category)

# API Key management routes
@app.route('/api/keys', methods=['GET'])
@local_access_only
def list_api_keys():
    keys = ApiKey.query.all()
    return render_template('api_keys.html', keys=keys)

@app.route('/api/keys/new', methods=['POST'])
@local_access_only
def create_api_key():
    description = request.form.get('description', '')
    new_key = ApiKey(key=ApiKey.generate_key(), description=description)

    db.session.add(new_key)
    db.session.commit()

    flash('New API key created successfully', 'success')
    return redirect(url_for('list_api_keys'))

@app.route('/api/keys/<int:key_id>/toggle', methods=['POST'])
@local_access_only
def toggle_api_key(key_id):
    key = ApiKey.query.get_or_404(key_id)
    key.is_active = not key.is_active

    db.session.commit()

    status = 'activated' if key.is_active else 'deactivated'
    flash(f'API key {status} successfully', 'success')
    return redirect(url_for('list_api_keys'))

@app.route('/add', methods=['GET', 'POST'])
@local_access_only
def add_form():
    if request.method == 'POST':
        question = request.form.get('question', '').strip()
        answer = request.form.get('answer', '').strip()
        category = request.form.get('category', '').lower()

        # Validate input
        if not question:
            flash('Question cannot be empty', 'error')
            return redirect(url_for('add_form'))

        if not answer:
            flash('Answer cannot be empty', 'error')
            return redirect(url_for('add_form'))

        if category not in ['riddle', 'joke', 'idiom']:
            flash('Invalid category', 'error')
            return redirect(url_for('add_form'))

        # Generate hash for deduplication
        content_hash = DataEntry.generate_hash(question, answer)

        # Check if entry already exists
        existing_entry = DataEntry.query.filter_by(content_hash=content_hash).first()
        if existing_entry:
            flash('This entry already exists in the database', 'error')
            return redirect(url_for('add_form'))

        # Create new entry
        new_entry = DataEntry(
            question=question,
            answer=answer,
            category=category,
            content_hash=content_hash
        )

        try:
            db.session.add(new_entry)
            db.session.commit()
            flash('Entry added successfully!', 'success')
            return redirect(url_for('browse'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding entry: {str(e)}', 'error')
            return redirect(url_for('add_form'))

    return render_template('add.html')

# LLM服务相关路由
@app.route('/api/llm/models', methods=['GET'])
@require_api_key
def list_llm_models():
    """获取可用的LLM模型列表"""
    try:
        from config import LLM_CONFIG

        # 检查LLM功能是否启用
        if not LLM_CONFIG.get('ENABLED', False):
            return jsonify({'error': 'LLM功能未启用'}), 403

        # 导入LLM服务
        from llm_service import get_available_models

        # 获取可用模型
        models = get_available_models()

        return jsonify({
            'models': models,
            'default_model': LLM_CONFIG.get('DEFAULT_MODEL', 'deepseek-chat')
        })
    except ImportError as e:
        return jsonify({'error': f'LLM服务模块加载失败: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'获取模型列表失败: {str(e)}'}), 500

@app.route('/api/llm/chat', methods=['POST'])
@require_api_key
def llm_chat():
    """LLM聊天接口"""
    try:
        from config import LLM_CONFIG

        # 检查LLM功能是否启用
        if not LLM_CONFIG.get('ENABLED', False):
            return jsonify({'error': 'LLM功能未启用'}), 403

        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据无效'}), 400

        # 验证必要字段
        if 'messages' not in data or not isinstance(data['messages'], list) or not data['messages']:
            return jsonify({'error': '消息列表不能为空'}), 400

        # 导入LLM服务
        from llm_service import chat_completion

        # 获取参数
        model = data.get('model', LLM_CONFIG.get('DEFAULT_MODEL', 'deepseek-chat'))
        temperature = data.get('temperature', LLM_CONFIG.get('DEFAULT_PARAMS', {}).get('temperature', 0.7))
        max_tokens = data.get('max_tokens', LLM_CONFIG.get('DEFAULT_PARAMS', {}).get('max_tokens', 1000))
        top_p = data.get('top_p', LLM_CONFIG.get('DEFAULT_PARAMS', {}).get('top_p', 0.9))

        # 调用LLM服务
        result = chat_completion(
            messages=data['messages'],
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p
        )

        return jsonify(result)
    except ImportError as e:
        return jsonify({'error': f'LLM服务模块加载失败: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'LLM聊天请求失败: {str(e)}'}), 500

@app.route('/api/llm/generate', methods=['POST'])
@require_api_key
def llm_generate():
    """LLM内容生成接口 - 简化版，只需要提供提示文本"""
    try:
        from config import LLM_CONFIG

        # 检查LLM功能是否启用
        if not LLM_CONFIG.get('ENABLED', False):
            return jsonify({'error': 'LLM功能未启用'}), 403

        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据无效'}), 400

        # 验证必要字段
        if 'prompt' not in data or not data['prompt']:
            return jsonify({'error': '提示文本不能为空'}), 400

        # 导入LLM服务
        from llm_service import chat_completion

        # 获取参数
        model = data.get('model', LLM_CONFIG.get('DEFAULT_MODEL', 'deepseek-chat'))
        temperature = data.get('temperature', LLM_CONFIG.get('DEFAULT_PARAMS', {}).get('temperature', 0.7))
        # 增加默认的max_tokens，以支持生成更多内容
        max_tokens = data.get('max_tokens', LLM_CONFIG.get('DEFAULT_PARAMS', {}).get('max_tokens', 2000))
        top_p = data.get('top_p', LLM_CONFIG.get('DEFAULT_PARAMS', {}).get('top_p', 0.9))

        # 构建系统提示，指导模型生成结构化内容
        system_message = {
            "role": "system",
            "content": "你是一个内容生成助手，擅长生成结构化的内容。请严格按照用户指定的格式生成内容，不要添加额外的解释或说明。"
        }

        # 构建消息，添加系统提示
        messages = [
            system_message,
            {"role": "user", "content": data['prompt']}
        ]

        # 调用LLM服务
        result = chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p
        )

        # 简化响应
        if 'choices' in result and len(result['choices']) > 0 and 'message' in result['choices'][0]:
            return jsonify({
                'text': result['choices'][0]['message'].get('content', ''),
                'model': result.get('model', model)
            })

        return jsonify(result)
    except ImportError as e:
        return jsonify({'error': f'LLM服务模块加载失败: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'LLM生成请求失败: {str(e)}'}), 500

# LLM管理界面
@app.route('/llm', methods=['GET'])
@local_access_only
def llm_dashboard():
    """LLM管理界面"""
    try:
        from config import LLM_CONFIG

        # 检查LLM功能是否启用
        if not LLM_CONFIG.get('ENABLED', False):
            flash('LLM功能未启用，请在config.py中启用', 'error')
            return redirect(url_for('index'))

        # 导入LLM服务
        from llm_service import get_available_models

        # 获取可用模型
        models = get_available_models()

        return render_template(
            'llm.html',
            models=models,
            default_model=LLM_CONFIG.get('DEFAULT_MODEL', 'deepseek-chat'),
            config=LLM_CONFIG
        )
    except ImportError as e:
        flash(f'LLM服务模块加载失败: {str(e)}', 'error')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'获取LLM信息失败: {str(e)}', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    # 使用0.0.0.0作为主机以允许外部访问API接口
    # Web管理界面通过装饰器限制只能从本地访问
    app.run(debug=True, host='0.0.0.0')
