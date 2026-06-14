"""
数据库初始化脚本（增量同步）
"""
import os
import re
from datetime import datetime
from app import create_app, db
from app.models import DataEntry, SyncState
from app.utils.logger import get_logger, log_exception

logger = get_logger()

DATA_DIR = "origin_data"

CATEGORY_MAPPING = {
    "riddle.txt": "riddle",
    "joke.txt": "joke",
    "idiom.txt": "idiom",
    "brain_teaser.txt": "brain_teaser",
    "trivia.txt": "trivia",
    "word_puzzle.txt": "word_puzzle"
}

ENTRY_PATTERN = re.compile(r'问题：(.*?)[\r\n]+答案:(.*)', re.DOTALL)


def parse_entries(text, category):
    entries = []
    for chunk in text.split('---'):
        chunk = chunk.strip()
        if not chunk:
            continue
        match = ENTRY_PATTERN.search(chunk)
        if match:
            question = match.group(1).strip()
            answer = match.group(2).strip()
            if question and answer:
                entries.append({"question": question, "answer": answer, "category": category})
    return entries


def sync_file(filename, category, existing_hashes):
    file_path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(file_path):
        return 0

    file_size = os.path.getsize(file_path)

    state = SyncState.query.filter_by(filename=filename).first()
    last_size = state.file_size if state else 0

    if file_size == last_size:
        logger.info(f"  {filename}: 无变化，跳过")
        return 0

    if file_size < last_size:
        last_size = 0
        logger.info(f"  {filename}: 文件变小，全量重扫")

    with open(file_path, 'r', encoding='utf-8') as f:
        if last_size > 0:
            f.seek(last_size)
            tail = f.read()
            if tail and not tail.startswith('---') and not tail.startswith('\n---'):
                f.seek(0)
                tail = f.read()
                last_size = 0
                logger.info(f"  {filename}: seek 位置不在条目边界，全量重扫")
            else:
                logger.info(f"  {filename}: 增量读取 {file_size - last_size} 字节")
        else:
            tail = f.read()
            logger.info(f"  {filename}: 全量读取 {file_size} 字节")

    entries = parse_entries(tail, category)
    added = 0
    for item in entries:
        content_hash = DataEntry.generate_hash(item["question"], item["answer"])
        if content_hash in existing_hashes:
            continue
        db.session.add(DataEntry(
            question=item["question"],
            answer=item["answer"],
            category=item["category"],
            content_hash=content_hash
        ))
        existing_hashes.add(content_hash)
        added += 1

    if state:
        state.file_size = file_size
        state.synced_at = datetime.utcnow()
    else:
        db.session.add(SyncState(filename=filename, file_size=file_size))

    return added


def init_db():
    try:
        app = create_app()
        with app.app_context():
            db.create_all()

            try:
                entry_count = DataEntry.query.count()
                logger.info(f"数据库已有 {entry_count} 个条目，开始增量同步...")

                if not os.path.exists(DATA_DIR):
                    logger.warning(f"数据目录 {DATA_DIR} 不存在")
                    return

                existing_hashes = {row[0] for row in db.session.query(DataEntry.content_hash).all()}

                total_added = 0
                for filename, category in CATEGORY_MAPPING.items():
                    added = sync_file(filename, category, existing_hashes)
                    if added > 0:
                        logger.info(f"  {filename}: 新增 {added} 条")
                    total_added += added

                db.session.commit()

                if total_added > 0:
                    logger.info(f"同步完成：新增 {total_added} 条，当前共 {entry_count + total_added} 条")
                else:
                    logger.info("同步完成：无新增条目")
            except Exception:
                log_exception(logger, "同步数据时出错")
                db.session.rollback()
    except Exception:
        logger.error("初始化数据库时出错")


if __name__ == "__main__":
    init_db()
