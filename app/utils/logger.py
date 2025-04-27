"""
日志工具模块
"""
import os
import logging
from logging.handlers import RotatingFileHandler
import sys
import traceback
from app.config import LOG_LEVEL, LOG_DIR

# 确保日志目录存在
def ensure_log_dir_exists(log_dir=LOG_DIR):
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    return log_dir

# 配置日志记录器
def setup_logger(name='puzzle', log_level=LOG_LEVEL, log_dir=LOG_DIR):
    """
    设置日志记录器，同时输出到控制台和文件

    Args:
        name: 日志记录器名称
        log_level: 日志级别
        log_dir: 日志文件目录

    Returns:
        配置好的日志记录器
    """
    # 确保日志目录存在
    log_dir = ensure_log_dir_exists(log_dir)

    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # 如果已经有处理器，不再添加
    if logger.handlers:
        return logger

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d:%(funcName)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 创建文件处理器 (每个文件最大10MB，保留5个备份)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, f'{name}.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# 默认日志记录器
app_logger = setup_logger('puzzle_app')
db_logger = setup_logger('puzzle_db')

def get_logger(module_name=None):
    """
    获取指定模块的日志记录器

    Args:
        module_name: 模块名称，如果为None，则使用调用者的模块名称

    Returns:
        配置好的日志记录器
    """
    if module_name is None:
        # 获取调用者的模块名称
        import inspect
        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        module_name = module.__name__ if module else 'unknown'

    # 创建或获取日志记录器
    return setup_logger(f'puzzle.{module_name}')

def log_exception(logger, message="An exception occurred", exc_info=None, level=logging.ERROR):
    """
    记录异常信息，包括完整的堆栈跟踪

    Args:
        logger: 日志记录器
        message: 日志消息
        exc_info: 异常信息，如果为None，则使用sys.exc_info()获取当前异常
        level: 日志级别，默认为ERROR
    """
    if exc_info is None:
        exc_info = sys.exc_info()

    if exc_info[0] is not None:  # 如果有异常
        # 获取完整的堆栈跟踪
        tb_str = ''.join(traceback.format_exception(*exc_info))
        # 记录异常信息
        logger.log(level, f"{message}:\n{tb_str}")
    else:
        # 如果没有异常，只记录消息
        logger.log(level, message)
