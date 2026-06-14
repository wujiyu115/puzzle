#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从下载的数据集导入知识问答数据到数据库。
数据源：
- xiehouyu.json (歇后语)
- idiom_data.json (成语)
"""

import hashlib
import json
import os
import random
import sqlite3
import sys

sys.stdout.reconfigure(line_buffering=True)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "data", "puzzle_data.db")
CATEGORY = "trivia"
TARGET = 10000


def generate_hash(question, answer):
    return hashlib.md5(f"{question}|{answer}".encode()).hexdigest()


def get_all_hashes(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT content_hash FROM data_entries")
    hashes = {row[0] for row in cur.fetchall()}
    conn.close()
    return hashes


def get_count(db_path, category):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM data_entries WHERE category=?", (category,))
    count = cur.fetchone()[0]
    conn.close()
    return count


def insert_batch(db_path, entries, category, existing_hashes):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    added = 0
    for q, a in entries:
        h = generate_hash(q, a)
        if h in existing_hashes:
            continue
        try:
            cur.execute(
                "INSERT INTO data_entries (question, answer, category, content_hash, created_at) "
                "VALUES (?, ?, ?, ?, datetime('now'))",
                (q, a, category, h)
            )
            existing_hashes.add(h)
            added += 1
        except sqlite3.IntegrityError:
            existing_hashes.add(h)
    conn.commit()
    conn.close()
    return added


def load_xiehouyu():
    path = os.path.join(SCRIPT_DIR, "xiehouyu.json")
    if not os.path.exists(path):
        print("xiehouyu.json 不存在")
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = []
    for item in data:
        riddle = item.get("riddle", "").strip()
        answer = item.get("answer", "").strip()
        if not riddle or not answer:
            continue
        if len(riddle) < 2 or len(answer) < 1:
            continue
        entries.append((f'歇后语"{riddle}"的下半句是什么？', answer))

    return entries


def load_idioms():
    path = os.path.join(SCRIPT_DIR, "idiom_data.json")
    if not os.path.exists(path):
        print("idiom_data.json 不存在")
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = []
    for item in data:
        word = item.get("word", "").strip()
        explanation = item.get("explanation", "").strip()
        pinyin = item.get("pinyin", "").strip()

        if not word or not explanation:
            continue
        if len(word) < 2 or len(explanation) < 4:
            continue
        explanation = explanation.rstrip("。").strip()

        entries.append((f'成语"{word}"是什么意思？', explanation))

        if pinyin:
            entries.append((f'成语"{word}"的拼音是什么？', pinyin))

    return entries


def main():
    if not os.path.exists(DB_PATH):
        print(f"数据库不存在: {DB_PATH}")
        sys.exit(1)

    existing_hashes = get_all_hashes(DB_PATH)
    current = get_count(DB_PATH, CATEGORY)
    print(f"[trivia] 当前 {current} 条，目标 {TARGET} 条")
    need = TARGET - current
    if need <= 0:
        print("已达标")
        return

    print(f"还需 {need} 条\n")

    xiehouyu = load_xiehouyu()
    print(f"歇后语: {len(xiehouyu)} 条")

    idioms = load_idioms()
    print(f"成语知识: {len(idioms)} 条")

    all_entries = xiehouyu + idioms
    random.shuffle(all_entries)

    unique = []
    seen = set()
    for q, a in all_entries:
        key = f"{q}|{a}"
        if key not in seen:
            seen.add(key)
            unique.append((q, a))
    print(f"去重后: {len(unique)} 条\n")

    batch_size = 1000
    total_added = 0
    for i in range(0, len(unique), batch_size):
        batch = unique[i:i + batch_size]
        added = insert_batch(DB_PATH, batch, CATEGORY, existing_hashes)
        total_added += added
        current = get_count(DB_PATH, CATEGORY)
        print(f"  批次 {i // batch_size + 1}: 新增 {added} 条, 总计 {current}/{TARGET}")
        if current >= TARGET:
            break

    print(f"\n最终: 新增 {total_added} 条, 总计 {get_count(DB_PATH, CATEGORY)} 条")


if __name__ == "__main__":
    main()
