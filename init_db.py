"""
数据库初始化脚本
"""
from app import create_app, db
from app.models import DataEntry
from app.utils.logger import get_logger, log_exception

# 获取当前模块的日志记录器
logger = get_logger()

# 示例数据
sample_data = [
    # Riddles
    {"question": "I'm tall when I'm young, and I'm short when I'm old. What am I?", "answer": "A candle", "category": "riddle"},
    {"question": "What has keys but no locks, space but no room, and you can enter but not go in?", "answer": "A keyboard", "category": "riddle"},
    {"question": "What has a head, a tail, is brown, and has no legs?", "answer": "A penny", "category": "riddle"},
    {"question": "What has an eye but cannot see?", "answer": "A needle", "category": "riddle"},
    {"question": "What can travel around the world while staying in a corner?", "answer": "A stamp", "category": "riddle"},

    # Jokes
    {"question": "Why don't scientists trust atoms?", "answer": "Because they make up everything!", "category": "joke"},
    {"question": "Did you hear about the mathematician who's afraid of negative numbers?", "answer": "He'll stop at nothing to avoid them!", "category": "joke"},
    {"question": "Why don't skeletons fight each other?", "answer": "They don't have the guts!", "category": "joke"},
    {"question": "What do you call a fake noodle?", "answer": "An impasta!", "category": "joke"},
    {"question": "Why did the scarecrow win an award?", "answer": "Because he was outstanding in his field!", "category": "joke"},

    # Idioms
    {"question": "A blessing in disguise", "answer": "Something good that isn't recognized at first", "category": "idiom"},
    {"question": "A dime a dozen", "answer": "Something common", "category": "idiom"},
    {"question": "Beat around the bush", "answer": "Avoid saying what you mean", "category": "idiom"},
    {"question": "Bite the bullet", "answer": "To get something over with", "category": "idiom"},
    {"question": "Break a leg", "answer": "Good luck", "category": "idiom"}
]

def init_db():
    """初始化数据库"""
    try:
        app = create_app()
        with app.app_context():
            # 创建表（如果不存在）
            db.create_all()
            logger.info("Database tables created or already exist")

            # 检查数据库是否为空
            try:
                entry_count = DataEntry.query.count()
                if entry_count == 0:
                    logger.info("Initializing database with sample data...")

                    # 添加示例数据
                    for item in sample_data:
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

                    db.session.commit()
                    logger.info(f"Added {len(sample_data)} sample entries")
                else:
                    logger.info(f"Database already contains {entry_count} entries. Skipping initialization.")
            except Exception as e:
                # 记录异常信息，包括完整的堆栈跟踪
                log_exception(logger, "Error checking or adding data")
                db.session.rollback()
    except Exception as e:
        # 记录异常信息，包括完整的堆栈跟踪
        log_exception(logger, "Error initializing database")

if __name__ == "__main__":
    init_db()
