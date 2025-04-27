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
        if category not in ['riddle', 'joke', 'idiom', 'brain_teaser']:
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
