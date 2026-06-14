"""
生成笑话数据到 origin_data/joke.txt
数据来源：
1. joke_data.json（原创笑话）
2. xiehouyu.json（歇后语，转为问答格式）
"""
import json
import hashlib
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_DIR, "origin_data", "joke.txt")
JOKE_JSON = os.path.join(SCRIPT_DIR, "joke_data.json")
XIEHOUYU_JSON = os.path.join(SCRIPT_DIR, "xiehouyu.json")
TARGET_COUNT = 10000


def generate_hash(q, a):
    return hashlib.md5(f"{q}|{a}".encode()).hexdigest()


def sanitize(text):
    return text.replace("---", "——").replace("--", "——").strip()


def load_existing():
    hashes = set()
    count = 0
    if not os.path.exists(OUTPUT_PATH):
        return hashes, count
    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    for chunk in content.split("---"):
        chunk = chunk.strip()
        if not chunk:
            continue
        lines = chunk.split("\n", 1)
        q = lines[0].replace("问题：", "").strip() if lines else ""
        a = lines[1].replace("答案:", "").strip() if len(lines) > 1 else ""
        if q and a:
            hashes.add(generate_hash(q, a))
            count += 1
    return hashes, count


def main():
    existing_hashes, existing_count = load_existing()
    print(f"已有 {existing_count} 条笑话")

    entries = []

    with open(JOKE_JSON, "r", encoding="utf-8") as f:
        jokes = json.load(f)
    for q, a in jokes:
        q, a = sanitize(q), sanitize(a)
        if not q or not a:
            continue
        h = generate_hash(q, a)
        if h not in existing_hashes:
            existing_hashes.add(h)
            entries.append((q, a))

    print(f"原创笑话：{len(entries)} 条新增")

    with open(XIEHOUYU_JSON, "r", encoding="utf-8") as f:
        xiehouyu = json.load(f)
    xhy_added = 0
    needed = TARGET_COUNT - existing_count - len(entries)
    for item in xiehouyu:
        if xhy_added >= needed:
            break
        riddle = item.get("riddle", "").strip()
        answer = item.get("answer", "").strip()
        if not riddle or not answer:
            continue
        if len(riddle) < 4 or len(answer) < 2:
            continue
        q = sanitize(riddle)
        a = sanitize(answer)
        h = generate_hash(q, a)
        if h not in existing_hashes:
            existing_hashes.add(h)
            entries.append((q, a))
            xhy_added += 1

    print(f"歇后语补充：{xhy_added} 条新增")

    with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
        for i, (q, a) in enumerate(entries):
            if existing_count > 0 or i > 0:
                f.write("---\n")
            f.write(f"问题：{q}\n答案:{a}\n")

    total = existing_count + len(entries)
    print(f"总计 {total} 条笑话")


if __name__ == "__main__":
    main()
