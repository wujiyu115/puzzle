"""
认证和授权工具
"""
from functools import wraps
from flask import request, jsonify, abort
from flask_login import current_user
from app.models import ApiKey
from datetime import datetime
from app import db
from app.utils.logger import get_logger

logger = get_logger('auth')


def require_api_key(f):
    """API密钥验证装饰器，允许已登录的session用户或有效API密钥"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            return f(*args, **kwargs)

        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')

        if not api_key:
            return jsonify({'error': 'API key is required'}), 401

        key = ApiKey.query.filter_by(key=api_key, is_active=True).first()
        if not key:
            return jsonify({'error': 'Invalid or inactive API key'}), 401

        key.last_used_at = datetime.utcnow()
        db.session.commit()

        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403, description="需要管理员权限")
        return f(*args, **kwargs)
    return decorated_function
