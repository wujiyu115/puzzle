#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从下载的数据集导入知识问答数据到 origin_data/trivia.txt。
数据源：
- xiehouyu.json (歇后语)
- idiom_data.json (成语)
"""

import hashlib
import json
import os
import random
import sys

sys.stdout.reconfigure(line_buffering=True)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "origin_data", "trivia.txt")
CATEGORY = "trivia"
TARGET = 10000


def generate_hash(question, answer):
    return hashlib.md5(f"{question}|{answer}".encode()).hexdigest()


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


def append_entries(entries, existing_hashes):
    added = 0
    with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
        for q, a in entries:
            q, a = sanitize(q), sanitize(a)
            h = generate_hash(q, a)
            if h in existing_hashes:
                continue
            existing_hashes.add(h)
            f.write(f"问题：{q}\n答案:{a}\n---\n")
            added += 1
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
    existing_hashes, current = load_existing()
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

    added = append_entries(unique, existing_hashes)
    final = current + added
    print(f"\n最终: 新增 {added} 条, 总计 {final} 条")


if __name__ == "__main__":
    main()
