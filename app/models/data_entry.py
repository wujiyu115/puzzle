"""
数据条目模型
"""
import hashlib
from datetime import datetime
from app import db

class DataEntry(db.Model):
    """数据条目模型，用于存储谜语、笑话和成语"""
    __tablename__ = 'data_entries'

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(10), nullable=False)
    content_hash = db.Column(db.String(32), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 为向后兼容
    @property
    def content(self):
        if self.category == 'idiom':
            return f"{self.question} - {self.answer}"
        return f"{self.question} {self.answer}"

    def __repr__(self):
        return f'<DataEntry {self.id}: {self.category}>'

    @staticmethod
    def generate_hash(question, answer):
        """生成问题和答案的MD5哈希以确保唯一性"""
        combined = f"{question}|{answer}"
        return hashlib.md5(combined.encode()).hexdigest()
