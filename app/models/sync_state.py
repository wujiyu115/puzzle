"""
文件同步状态模型
"""
from datetime import datetime
from app import db


class SyncState(db.Model):
    __tablename__ = 'sync_state'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), unique=True, nullable=False)
    file_size = db.Column(db.Integer, nullable=False, default=0)
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<SyncState {self.filename}: {self.file_size}B>'
