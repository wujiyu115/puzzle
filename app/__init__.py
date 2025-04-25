"""
Puzzle Collection Application
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# 初始化数据库
db = SQLAlchemy()

def create_app():
    """创建并配置Flask应用"""
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    
    # 配置
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///data/puzzle_data.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 初始化扩展
    db.init_app(app)
    
    # 确保数据目录存在
    with app.app_context():
        from app.utils.logger import get_logger, log_exception
        logger = get_logger('app')
        
        try:
            # # 确保数据目录存在
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']
            if db_uri.startswith('sqlite:///'):
                db_path = db_uri.replace('sqlite:///', '')
                if not os.path.isabs(db_path):
                    db_path = os.path.join(os.getcwd(), db_path)
                
                # 创建目录（如果不存在）
                db_dir = os.path.dirname(db_path)
                if db_dir and not os.path.exists(db_dir):
                    os.makedirs(db_dir)
                    logger.info(f"Created directory: {db_dir}")
            
            # 创建所有表
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            log_exception(logger, f"Error creating database tables")
    
    # 注册上下文处理器
    from datetime import datetime
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}
    
    # 注册蓝图
    from app.routes.main import main_bp
    from app.routes.api import api_bp
    from app.routes.admin import admin_bp
    from app.routes.llm import llm_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp)
    app.register_blueprint(llm_bp, url_prefix='/api/llm')
    
    return app
