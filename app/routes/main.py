"""
主要路由模块
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models import DataEntry
from app.utils.auth import local_access_only
from app.utils.logger import get_logger, log_exception

# 获取当前模块的日志记录器
logger = get_logger()

# 创建蓝图
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@local_access_only
def index():
    """首页"""
    return render_template('index.html')

@main_bp.route('/browse')
@local_access_only
def browse():
    """浏览数据条目"""
    category = request.args.get('category')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    query = DataEntry.query
    if category:
        query = query.filter_by(category=category)
    
    pagination = query.order_by(DataEntry.created_at.desc()).paginate(page=page, per_page=per_page)
    entries = pagination.items
    
    return render_template('browse.html', entries=entries, pagination=pagination, category=category)

@main_bp.route('/add', methods=['GET', 'POST'])
@local_access_only
def add_form():
    """添加新条目表单"""
    if request.method == 'POST':
        question = request.form.get('question', '').strip()
        answer = request.form.get('answer', '').strip()
        category = request.form.get('category', '').lower()
        
        # 验证输入
        if not question:
            flash('Question cannot be empty', 'error')
            return redirect(url_for('main.add_form'))
        
        if not answer:
            flash('Answer cannot be empty', 'error')
            return redirect(url_for('main.add_form'))
        
        if category not in ['riddle', 'joke', 'idiom']:
            flash('Invalid category', 'error')
            return redirect(url_for('main.add_form'))
        
        # 生成哈希用于去重
        content_hash = DataEntry.generate_hash(question, answer)
        
        # 检查条目是否已存在
        existing_entry = DataEntry.query.filter_by(content_hash=content_hash).first()
        if existing_entry:
            flash('This entry already exists in the database', 'error')
            return redirect(url_for('main.add_form'))
        
        # 创建新条目
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
            return redirect(url_for('main.browse'))
        except Exception as e:
            db.session.rollback()
            # 记录异常信息，包括完整的堆栈跟踪
            log_exception(logger, "Error adding entry via web form")
            flash(f'Error adding entry: {str(e)}', 'error')
            return redirect(url_for('main.add_form'))
    
    return render_template('add.html')
