"""
API密钥模型
"""
import os
import hashlib
from datetime import datetime
from app import db

class ApiKey(db.Model):
    """API密钥模型，用于API访问控制"""
    __tablename__ = 'api_keys'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime)

    @staticmethod
    def generate_key():
        """生成随机API密钥"""
        return hashlib.sha256(os.urandom(32)).hexdigest()
