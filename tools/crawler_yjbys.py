#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 yjbys.com 的脑筋急转弯文章中提取 Q&A 对，写入数据库。
"""

import hashlib
import os
import re
import sqlite3
import sys
import time
import random
import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(line_buffering=True)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "data", "puzzle_data.db")
TARGET = 10000

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def generate_hash(question, answer):
    return hashlib.md5(f"{question}|{answer}".encode()).hexdigest()


def get_existing_hashes(db_path):
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


def insert_entries_batch(db_path, entries, category, existing_hashes):
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


def extract_qa_from_article(url):
    try:
        resp = SESSION.get(url, timeout=15)
        if resp.status_code != 200:
            return []
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    content = soup.select_one("div.content")
    if not content:
        return []

    pairs = []
    for p in content.select("p"):
        text = p.get_text().strip()
        if not text or len(text) < 5:
            continue

        # Pattern: "数字、问题？答案：答案"
        m = re.match(r'^\d+[\.\、．\)）]\s*(.+?)答案[：:]\s*(.+)', text)
        if m:
            question = m.group(1).strip().rstrip("？?—— \t")
            answer = m.group(2).strip().rstrip("。.）)")
            if question and answer and len(question) > 3 and len(answer) > 0:
                pairs.append((question, answer))
            continue

        # Pattern: "问题？——答案"
        m2 = re.match(r'^(?:\d+[\.\、．\)）]\s*)?(.+?)[？?]\s*[——\-]+\s*答案?[：:]?\s*(.+)', text)
        if m2:
            question = m2.group(1).strip()
            answer = m2.group(2).strip().rstrip("。.）)")
            if question and answer and len(question) > 3:
                pairs.append((question, answer))
            continue

    return pairs


def collect_article_links():
    base_url = "https://www.yjbys.com/naojinjizhuanwan/"
    all_links = set()

    for page in range(1, 30):
        if page == 1:
            url = base_url
        else:
            url = f"{base_url}index_{page}.html"

        try:
            resp = SESSION.get(url, timeout=10)
            if resp.status_code != 200:
                break
        except Exception:
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select("a"):
            href = a.get("href", "")
            if "/naojinjizhuanwan/" in href and re.search(r'/\d+\.html$', href):
                all_links.add(href)

    return sorted(all_links)


def main():
    print(f"当前脑筋急转弯: {get_count(DB_PATH, 'brain_teaser')}/{TARGET}")

    existing_hashes = get_existing_hashes(DB_PATH)
    print(f"已有 {len(existing_hashes)} 条去重哈希")

    print("收集文章链接...")
    links = collect_article_links()
    print(f"找到 {len(links)} 篇文章")

    total_added = 0
    for i, url in enumerate(links):
        current = get_count(DB_PATH, "brain_teaser")
        if current >= TARGET:
            print(f"[DONE] 已达到 {current} 条!")
            break

        pairs = extract_qa_from_article(url)
        if pairs:
            added = insert_entries_batch(DB_PATH, pairs, "brain_teaser", existing_hashes)
            total_added += added
            current = get_count(DB_PATH, "brain_teaser")
            print(f"  [{i+1}/{len(links)}] {url.split('/')[-1]}: {len(pairs)} 条, 新增 {added}, 总计 {current}/{TARGET}")

        time.sleep(random.uniform(0.5, 1.5))

    print(f"\nyjbys.com 新增 {total_added} 条")
    print(f"脑筋急转弯: {get_count(DB_PATH, 'brain_teaser')}")


if __name__ == "__main__":
    main()
