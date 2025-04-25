"""
认证和授权工具
"""
import re
from functools import wraps
from flask import request, jsonify, abort
from app.models import ApiKey
from datetime import datetime
from app import db
from app.config import LOCAL_NETWORK_IPS

# 检查请求是否来自本地网络
def is_local_request():
    """
    检查请求是否来自本地网络/本地主机
    
    根据config.py中的LOCAL_NETWORK_IPS配置检查请求IP是否在允许的本地网络范围内
    支持精确匹配和正则表达式模式匹配
    """
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

# API密钥验证装饰器
def require_api_key(f):
    """API密钥验证装饰器，用于API端点"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查请求是否来自本地网络
        if is_local_request():
            # 对本地网络请求跳过API密钥验证
            return f(*args, **kwargs)
        
        # 对非本地请求，要求API密钥
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({'error': 'API key is required'}), 401
        
        # 检查API密钥是否存在且有效
        key = ApiKey.query.filter_by(key=api_key, is_active=True).first()
        if not key:
            return jsonify({'error': 'Invalid or inactive API key'}), 401
        
        # 更新最后使用时间戳
        key.last_used_at = datetime.utcnow()
        db.session.commit()
        
        return f(*args, **kwargs)
    return decorated_function

# 仅本地访问装饰器
def local_access_only(f):
    """仅本地访问装饰器，用于管理/管理员路由"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查请求是否来自本地主机
        if not is_local_request():
            abort(403, description="Access denied. This page is only accessible from localhost.")
        return f(*args, **kwargs)
    return decorated_function
