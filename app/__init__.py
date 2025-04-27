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
    
    # 确保数据库URI使用正确的路径格式
    db_uri = os.environ.get('SQLALCHEMY_DATABASE_URI')
    if not db_uri:
        # 获取应用根目录
        app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        # 使用绝对路径构建数据库URI
        data_dir = os.path.join(app_root, 'data')
        db_path = os.path.join(data_dir, 'puzzle_data.db')
        # 规范化路径并转换为URI格式
        db_path = os.path.normpath(db_path)
        db_uri = f'sqlite:///{db_path}'
    
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 初始化扩展
    db.init_app(app)
    
    # 确保数据目录存在
    with app.app_context():
        from app.utils.logger import get_logger, log_exception
        logger = get_logger('app')
        
        try:
            # 确保数据目录存在
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']
            if db_uri.startswith('sqlite:///'):
                db_path = db_uri.replace('sqlite:///', '')
                
                # 处理相对路径，确保路径解析正确
                if not os.path.isabs(db_path):
                    # 获取应用根目录（app.py所在目录）
                    app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                    db_path = os.path.join(app_root, db_path)
                    
                    # 规范化路径分隔符，确保跨平台兼容性
                    db_path = os.path.normpath(db_path)
                    logger.info(f"Resolved database path: {db_path}")
                
                # 创建目录（如果不存在）
                db_dir = os.path.dirname(db_path)
                if db_dir and not os.path.exists(db_dir):
                    try:
                        os.makedirs(db_dir, exist_ok=True)
                        logger.info(f"Created directory: {db_dir}")
                    except PermissionError as pe:
                        logger.error(f"Permission error creating directory {db_dir}: {str(pe)}")
                        raise
                    except Exception as ex:
                        logger.error(f"Error creating directory {db_dir}: {str(ex)}")
                        raise
                
                # 验证数据库目录是否可写
                if not os.access(db_dir, os.W_OK):
                    logger.error(f"Database directory is not writable: {db_dir}")
                    raise PermissionError(f"Database directory is not writable: {db_dir}")
            
            # 创建所有表
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {db_uri}")
            logger.error(f"Exception details: {str(e)}")
            log_exception(logger, "Error creating database tables")
    
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
