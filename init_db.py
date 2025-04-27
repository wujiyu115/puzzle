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
    # Riddles (谜语)
    {"question": "我年轻时高大，年老时矮小。我是什么？", "answer": "蜡烛", "category": "riddle"},
    {"question": "有键盘没有锁，有空间没有房间，你能进入但不能进去。我是什么？", "answer": "键盘", "category": "riddle"},
    {"question": "有头有尾，是棕色的，没有腿。我是什么？", "answer": "一分钱硬币", "category": "riddle"},
    {"question": "有眼睛但看不见。我是什么？", "answer": "针", "category": "riddle"},
    {"question": "能环游世界却始终待在角落里。我是什么？", "answer": "邮票", "category": "riddle"},

    # Jokes (笑话)
    {"question": "为什么科学家不相信原子？", "answer": "因为它们编造了一切！", "category": "joke"},
    {"question": "你听说过那个害怕负数的数学家吗？", "answer": "他会不遗余力地避开它们！", "category": "joke"},
    {"question": "为什么骷髅们不互相打架？", "answer": "因为他们没有勇气（肠子）！", "category": "joke"},
    {"question": "你怎么称呼一个假的面条？", "answer": "冒牌意大利面！", "category": "joke"},
    {"question": "为什么稻草人获得了奖项？", "answer": "因为他在自己的领域里表现突出！", "category": "joke"},

    # Idioms (成语)
    {"question": "塞翁失马", "answer": "祸福相依，失去的未必不是好事", "category": "idiom"},
    {"question": "司空见惯", "answer": "常见的事物，不足为奇", "category": "idiom"},
    {"question": "拐弯抹角", "answer": "说话不直接，绕来绕去", "category": "idiom"},
    {"question": "破釜沉舟", "answer": "下定决心，不留退路", "category": "idiom"},
    {"question": "马到成功", "answer": "祝愿一切顺利，很快成功", "category": "idiom"},

    # Brain Teasers (脑筋急转弯)
    {"question": "什么东西越洗越脏？", "answer": "洗澡水", "category": "brain_teaser"},
    {"question": "什么东西黑人用了变白，白人用了变黑？", "answer": "牙膏", "category": "brain_teaser"},
    {"question": "什么门永远关不上？", "answer": "问题", "category": "brain_teaser"},
    {"question": "什么东西有头无脚？", "answer": "钉子", "category": "brain_teaser"},
    {"question": "什么东西晚上才会长出来？", "answer": "星星", "category": "brain_teaser"}
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
