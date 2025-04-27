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
    """批量添加条目表单"""
    if request.method == 'POST':
        return process_batch_entries(request)

    return render_template('add.html')

def process_batch_entries(request):
    """处理批量添加条目"""
    batch_entries = request.form.get('batch_entries', '').strip()
    category = request.form.get('batch_category', '').lower()

    # 验证输入
    if not batch_entries:
        flash('批量条目不能为空', 'error')
        return redirect(url_for('main.add_form'))

    if category not in ['riddle', 'joke', 'idiom']:
        flash('无效的类别', 'error')
        return redirect(url_for('main.add_form'))

    # 解析批量条目
    entries = []

    # 根据类别确定分隔符
    if category == 'riddle' or category == 'joke':
        separator = '答案：'
    else:  # idiom
        separator = '含义：'

    # 分割多个条目
    items = batch_entries.split('---')

    success_count = 0
    duplicate_count = 0
    failed_count = 0

    for item in items:
        item = item.strip()
        if not item:
            continue

        # 分割问题和答案
        parts = item.split(separator, 1)

        if len(parts) < 2:
            failed_count += 1
            continue

        question = parts[0].strip()
        answer = parts[1].strip()

        if not question or not answer:
            failed_count += 1
            continue

        # 生成哈希用于去重
        content_hash = DataEntry.generate_hash(question, answer)

        # 检查条目是否已存在
        existing_entry = DataEntry.query.filter_by(content_hash=content_hash).first()
        if existing_entry:
            duplicate_count += 1
            continue

        # 创建新条目
        new_entry = DataEntry(
            question=question,
            answer=answer,
            category=category,
            content_hash=content_hash
        )

        try:
            db.session.add(new_entry)
            success_count += 1
        except Exception as e:
            log_exception(logger, f"Error adding batch entry: {str(e)}")
            failed_count += 1

    # 提交事务
    if success_count > 0:
        try:
            db.session.commit()
            flash(f'成功添加 {success_count} 个条目！{duplicate_count} 个重复，{failed_count} 个失败。', 'success')
        except Exception as e:
            db.session.rollback()
            log_exception(logger, "Error committing batch entries")
            flash(f'提交批量条目时出错: {str(e)}', 'error')
    else:
        if duplicate_count > 0:
            flash(f'未添加任何条目。{duplicate_count} 个重复，{failed_count} 个失败。', 'warning')
        else:
            flash('未添加任何条目。请检查输入格式。', 'error')

    return redirect(url_for('main.browse'))
