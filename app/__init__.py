"""
Puzzle Collection Application
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from app.utils.logger import get_logger, log_exception
logger = get_logger('app')

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录'
login_manager.login_message_category = 'error'

def create_app():
    """创建并配置Flask应用"""
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-testing')

    db_uri = os.environ.get('SQLALCHEMY_DATABASE_URI')
    if not db_uri:
        app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        data_dir = os.path.join(app_root, 'data')
        db_path = os.path.join(data_dir, 'puzzle_data.db')
        db_path = os.path.normpath(db_path)
        db_uri = f'sqlite:///{db_path}'
        logger.info(f"Resolved init database path: {db_path}")

    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    with app.app_context():
        try:
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']
            if db_uri.startswith('sqlite:///'):
                db_path = db_uri.replace('sqlite:///', '')

                if not os.path.isabs(db_path):
                    app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                    db_path = os.path.join(app_root, db_path)
                    db_path = os.path.normpath(db_path)
                    logger.info(f"Resolved database path: {db_path}")

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

                if not os.access(db_dir, os.W_OK):
                    logger.error(f"Database directory is not writable: {db_dir}")
                    raise PermissionError(f"Database directory is not writable: {db_dir}")

            from app import models  # noqa: F401
            db.create_all()
            logger.info("Database tables created successfully")

            _seed_admin()
        except Exception as e:
            logger.error(f"Error creating database tables: {db_uri}")

    from datetime import datetime
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}

    from app.routes.main import main_bp
    from app.routes.api import api_bp
    from app.routes.admin import admin_bp
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp)

    return app


def _seed_admin():
    """首次启动时创建默认管理员账户"""
    from app.models import User
    if User.query.count() == 0:
        admin = User(username='admin', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        logger.info("Created default admin user (admin / admin123)")
