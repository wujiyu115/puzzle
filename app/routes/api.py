"""
API路由模块
"""
from flask import Blueprint, request, jsonify, session
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
    source = request.args.get('source')

    query = DataEntry.query
    if category:
        query = query.filter_by(category=category)

    total_entries = query.count()
    if total_entries == 0:
        return jsonify([])

    if count > total_entries:
        count = total_entries

    # 基于 source 参数做 session 级去重
    seen_ids = []
    seen_key = None
    if source:
        seen_key = f'seen_{source}'
        seen_ids = session.get(seen_key, [])
        if seen_ids:
            filtered_query = query.filter(~DataEntry.id.in_(seen_ids))
            available = filtered_query.count()
            if available >= count:
                query = filtered_query
            else:
                seen_ids = []

    random_entries = query.order_by(db.func.random()).limit(count).all()

    if seen_key is not None:
        seen_ids.extend([entry.id for entry in random_entries])
        session[seen_key] = seen_ids

    result = [{
        'id': entry.id,
        'question': entry.question,
        'answer': entry.answer,
        'category': entry.category,
        'created_at': entry.created_at.isoformat()
    } for entry in random_entries]

    return jsonify(result)

@api_bp.route('/add', methods=['POST'])
@require_api_key
def add_entry():
    """批量添加多个条目"""
    data = request.get_json()

    # 确保数据是列表格式
    if not data or not isinstance(data, list):
        return jsonify({'error': '请求数据必须是条目数组'}), 400

    # 批量添加
    return add_multiple_entries(data)

def add_multiple_entries(entries):
    """批量添加多个条目"""
    if not entries:
        return jsonify({'error': 'No entries provided'}), 400

    results = {
        'success': [],
        'failed': [],
        'duplicates': []
    }

    for entry in entries:
        # 检查新格式（问题/答案）
        if 'question' in entry and 'answer' in entry and 'category' in entry:
            question = entry['question'].strip()
            answer = entry['answer'].strip()
            category = entry['category'].lower()

            # 验证字段
            if not question or not answer:
                results['failed'].append({
                    'entry': entry,
                    'reason': 'Question and answer cannot be empty'
                })
                continue
        else:
            results['failed'].append({
                'entry': entry,
                'reason': 'Missing required fields'
            })
            continue

        # 验证类别
        if category not in ['riddle', 'joke', 'idiom', 'brain_teaser', 'trivia', 'word_puzzle']:
            results['failed'].append({
                'entry': entry,
                'reason': 'Invalid category. Must be one of: riddle, joke, idiom, brain_teaser'
            })
            continue

        # 生成哈希用于去重
        content_hash = DataEntry.generate_hash(question, answer)

        # 检查条目是否已存在
        existing_entry = DataEntry.query.filter_by(content_hash=content_hash).first()
        if existing_entry:
            results['duplicates'].append({
                'entry': entry,
                'existing_id': existing_entry.id
            })
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
            # 先不提交，等所有条目处理完再一次性提交
        except Exception as e:
            results['failed'].append({
                'entry': entry,
                'reason': str(e)
            })
            continue

        # 添加到成功列表（暂时没有ID，提交后再更新）
        results['success'].append({
            'temp_index': len(results['success']),
            'question': question,
            'answer': answer,
            'category': category
        })

    # 如果有成功添加的条目，提交事务
    if results['success']:
        try:
            db.session.commit()

            # 查询刚刚添加的条目，获取它们的ID
            for i, entry in enumerate(results['success']):
                # 使用哈希查找刚添加的条目
                content_hash = DataEntry.generate_hash(entry['question'], entry['answer'])
                db_entry = DataEntry.query.filter_by(content_hash=content_hash).first()

                if db_entry:
                    # 更新成功列表中的条目，添加ID和创建时间
                    results['success'][i] = {
                        'id': db_entry.id,
                        'question': db_entry.question,
                        'answer': db_entry.answer,
                        'category': db_entry.category,
                        'created_at': db_entry.created_at.isoformat()
                    }
        except Exception as e:
            db.session.rollback()
            # 记录异常信息，包括完整的堆栈跟踪
            log_exception(logger, "Failed to commit batch entries via API")
            return jsonify({
                'error': f'Failed to add entries: {str(e)}',
                'partial_results': results
            }), 500

    # 返回结果
    return jsonify(results), 201
