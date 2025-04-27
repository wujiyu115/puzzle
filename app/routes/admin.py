"""
管理路由模块
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models import ApiKey
from app.utils.auth import local_access_only

# 创建蓝图
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/api/keys', methods=['GET'])
@local_access_only
def list_api_keys():
    """列出所有API密钥"""
    keys = ApiKey.query.all()
    return render_template('api_keys.html', keys=keys)

@admin_bp.route('/api/keys/new', methods=['POST'])
@local_access_only
def create_api_key():
    """创建新的API密钥"""
    description = request.form.get('description', '')
    new_key = ApiKey(key=ApiKey.generate_key(), description=description)
    
    db.session.add(new_key)
    db.session.commit()
    
    flash('New API key created successfully', 'success')
    return redirect(url_for('admin.list_api_keys'))

@admin_bp.route('/api/keys/<int:key_id>/toggle', methods=['POST'])
@local_access_only
def toggle_api_key(key_id):
    """切换API密钥的激活状态"""
    key = ApiKey.query.get_or_404(key_id)
    key.is_active = not key.is_active
    
    db.session.commit()
    
    status = 'activated' if key.is_active else 'deactivated'
    flash(f'API key {status} successfully', 'success')
    return redirect(url_for('admin.list_api_keys'))
