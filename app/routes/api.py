"""
API路由模块
"""
from flask import Blueprint, request, jsonify
from app import db
from app.models import DataEntry
from app.utils.auth import require_api_key
from app.utils.logger import get_logger, log_exception

# 获取当前模块的日志记录器
logger = get_logger()

# 创建蓝图
api_bp = Blueprint('api', __name__)

@api_bp.route('/random/<int:count>', methods=['GET'])
@require_api_key
def get_random_entries(count):
    """获取随机条目"""
    category = request.args.get('category')
    
    query = DataEntry.query
    if category:
        query = query.filter_by(category=category)
    
    # 获取匹配条目的总数
    total_entries = query.count()
    
    # 如果请求的数量超过可用数量，返回所有可用的
    if count > total_entries:
        count = total_entries
    
    # 获取随机条目
    if total_entries > 0:
        # SQLite特定的随机排序
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

@api_bp.route('/add', methods=['POST'])
@require_api_key
def add_entry():
    """添加新条目"""
    data = request.get_json()
    
    # 检查新格式（问题/答案）
    if data and 'question' in data and 'answer' in data and 'category' in data:
        question = data['question'].strip()
        answer = data['answer'].strip()
        category = data['category'].lower()
        
        # 验证字段
        if not question or not answer:
            return jsonify({'error': 'Question and answer cannot be empty'}), 400
    # 检查旧格式（内容）
    elif data and 'content' in data and 'category' in data:
        content = data['content'].strip()
        category = data['category'].lower()
        
        # 验证内容
        if not content:
            return jsonify({'error': 'Content cannot be empty'}), 400
        
        # 根据类别将内容拆分为问题和答案
        if category == 'riddle' or category == 'joke':
            # 对于谜语和笑话，尝试在问号处分割
            parts = content.split('?', 1)
            if len(parts) > 1:
                question = parts[0].strip() + '?'
                answer = parts[1].strip()
            else:
                # 如果没有问号，将整个内容作为问题
                question = content
                answer = "No answer provided"
        elif category == 'idiom':
            # 对于成语，在破折号处分割
            parts = content.split('-', 1)
            if len(parts) > 1:
                question = parts[0].strip()
                answer = parts[1].strip()
            else:
                # 如果没有破折号，将整个内容作为问题
                question = content
                answer = "No meaning provided"
        else:
            question = content
            answer = ""
    else:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # 验证类别
    if category not in ['riddle', 'joke', 'idiom']:
        return jsonify({'error': 'Invalid category. Must be one of: riddle, joke, idiom'}), 400
    
    # 生成哈希用于去重
    content_hash = DataEntry.generate_hash(question, answer)
    
    # 检查条目是否已存在
    existing_entry = DataEntry.query.filter_by(content_hash=content_hash).first()
    if existing_entry:
        return jsonify({'error': 'This entry already exists in the database'}), 409
    
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
        return jsonify({
            'id': new_entry.id,
            'question': new_entry.question,
            'answer': new_entry.answer,
            'category': new_entry.category,
            'created_at': new_entry.created_at.isoformat()
        }), 201
    except Exception as e:
        db.session.rollback()
        # 记录异常信息，包括完整的堆栈跟踪
        log_exception(logger, "Failed to add entry via API")
        return jsonify({'error': f'Failed to add entry: {str(e)}'}), 500
