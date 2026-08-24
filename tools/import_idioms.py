"""
从 idiom_data.json 导入成语数据到 origin_data/idiom.txt
"""
import json
import hashlib
import os

from clean_data import append_entries as write_entries

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
JSON_PATH = os.path.join(SCRIPT_DIR, "idiom_data.json")
OUTPUT_PATH = os.path.join(PROJECT_DIR, "origin_data", "idiom.txt")
TARGET_COUNT = 5000


def generate_hash(question, answer):
    return hashlib.md5(f"{question}|{answer}".encode()).hexdigest()


def load_existing():
    hashes = set()
    if not os.path.exists(OUTPUT_PATH):
        return hashes, ""
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
    return hashes, content


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    existing_hashes, existing_content = load_existing()
    print(f"已有 {len(existing_hashes)} 条成语")

    needed = TARGET_COUNT - len(existing_hashes)
    if needed <= 0:
        print(f"已达标 {len(existing_hashes)} 条，无需导入")
        return

    entries = []
    for item in data:
        word = item.get("word", "").strip()
        explanation = item.get("explanation", "").strip()
        if not word or not explanation:
            continue
        if len(word) < 2:
            continue
        h = generate_hash(word, explanation)
        if h in existing_hashes:
            continue
        entries.append((word, explanation))
        if len(entries) >= needed:
            break

    added = write_entries(OUTPUT_PATH, entries, existing_hashes)

    print(f"新增 {added} 条成语，总计约 {len(existing_hashes)} 条")


if __name__ == "__main__":
    main()
