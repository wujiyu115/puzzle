"""
数据库初始化脚本
"""
import os
import re
from app import create_app, db
from app.models import DataEntry
from app.utils.logger import get_logger, log_exception

# 获取当前模块的日志记录器
logger = get_logger()

# 数据文件目录
DATA_DIR = "origin_data"

# 类别映射（文件名到类别的映射）
CATEGORY_MAPPING = {
    "riddle.txt": "riddle",
    "joke.txt": "joke",
    "idiom.txt": "idiom",
    "brain_teaser.txt": "brain_teaser"
}

def load_data_from_files():
    """从文件中加载数据"""
    data = []

    # 检查数据目录是否存在
    if not os.path.exists(DATA_DIR):
        logger.warning(f"数据目录 {DATA_DIR} 不存在")
        return data

    # 遍历数据目录中的所有文件
    for filename in os.listdir(DATA_DIR):
        if filename in CATEGORY_MAPPING:
            category = CATEGORY_MAPPING[filename]
            file_path = os.path.join(DATA_DIR, filename)

            try:
                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 分割条目
                entries = content.split('---')

                for entry in entries:
                    entry = entry.strip()
                    if not entry:
                        continue

                    # 解析问题和答案
                    match = re.search(r'问题：(.*?)[\r\n]+答案:(.*)', entry, re.DOTALL)
                    if match:
                        question = match.group(1).strip()
                        answer = match.group(2).strip()

                        if question and answer:
                            data.append({
                                "question": question,
                                "answer": answer,
                                "category": category
                            })
                    else:
                        logger.warning(f"无法解析条目: {entry[:50]}...")

                logger.info(f"从 {filename} 加载了 {len(entries)} 个条目")
            except Exception as e:
                logger.error(f"加载文件 {filename} 时出错: {str(e)}")

    logger.info(f"总共加载了 {len(data)} 个条目")
    return data

def init_db():
    """初始化数据库"""
    try:
        app = create_app()
        with app.app_context():
            # 创建表（如果不存在）
            db.create_all()
            logger.info("数据库表已创建或已存在")

            # 检查数据库是否为空
            try:
                entry_count = DataEntry.query.count()
                if entry_count == 0:
                    logger.info("正在从文件加载数据初始化数据库...")

                    # 从文件加载数据
                    data = load_data_from_files()

                    if not data:
                        logger.warning("没有找到数据文件或数据文件为空")
                        return

                    # 添加数据
                    added_count = 0
                    for item in data:
                        # 为问题和答案生成哈希
                        content_hash = DataEntry.generate_hash(item["question"], item["answer"])

                        # 检查条目是否已存在
                        existing = DataEntry.query.filter_by(content_hash=content_hash).first()
                        if not existing:
                            entry = DataEntry(
                                question=item["question"],
                                answer=item["answer"],
                                category=item["category"],
                                content_hash=content_hash
                            )
                            db.session.add(entry)
                            added_count += 1

                    db.session.commit()
                    logger.info(f"已添加 {added_count} 个条目")
                else:
                    logger.info(f"数据库已包含 {entry_count} 个条目，跳过初始化。")
            except Exception:
                # 记录异常信息，包括完整的堆栈跟踪
                log_exception(logger, "检查或添加数据时出错")
                db.session.rollback()
    except Exception:
        # 记录异常信息，包括完整的堆栈跟踪
        logger.error("初始化数据库时出错")
        # log_exception(logger, "初始化数据库时出错")

if __name__ == "__main__":
    init_db()
