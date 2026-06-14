#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 cmiyu.com 谜语精选和谜语库4 爬取脑筋急转弯风格条目，补足到10,000条。
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
BASE_URL = "http://www.cmiyu.com"
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


def fetch_page(url, retries=3):
    for attempt in range(retries):
        try:
            resp = SESSION.get(url, timeout=15)
            if resp.status_code == 200:
                resp.encoding = "gb18030"
                return resp.text
            if resp.status_code == 404:
                return None
        except Exception as e:
            if attempt == retries - 1:
                print(f"  [WARN] {url}: {e}")
        time.sleep(random.uniform(0.3, 0.8))
    return None


def extract_answer_from_detail(url):
    html = fetch_page(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    md = soup.select_one("div.md")
    if not md:
        return None
    h3_list = md.select("h3")
    for h3 in h3_list:
        text = h3.get_text().strip()
        if text.startswith("答：") or text.startswith("答:"):
            return text[2:].strip()
        if "谜底：" in text:
            return text.replace("谜底：", "").strip()
        if "谜底:" in text:
            return text.replace("谜底:", "").strip()
    if len(h3_list) >= 2:
        answer_text = h3_list[1].get_text().strip()
        answer_text = re.sub(r'^(答[：:]|谜底[：:])\s*', '', answer_text)
        if answer_text:
            return answer_text
    return None


def crawl_section(section_path, prefix, max_page, existing_hashes):
    total_added = 0
    consecutive_empty = 0

    for page_num in range(1, max_page + 1):
        current = get_count(DB_PATH, "brain_teaser")
        if current >= TARGET:
            print(f"  [DONE] 已达到 {current} 条!")
            return total_added

        if page_num == 1:
            page_url = BASE_URL + section_path
        else:
            page_url = f"{BASE_URL}{section_path}{prefix}{page_num}.html"

        html = fetch_page(page_url)
        if not html:
            consecutive_empty += 1
            if consecutive_empty >= 5:
                break
            continue

        soup = BeautifulSoup(html, "html.parser")
        items = soup.select("div.list > ul > li")
        if not items:
            consecutive_empty += 1
            if consecutive_empty >= 5:
                break
            continue

        consecutive_empty = 0
        page_entries = []

        for item in items:
            a = item.select_one("a")
            if not a:
                continue
            question = a.get_text().strip()
            href = a.get("href")
            if not question or not href:
                continue

            q_clean = re.sub(r'^(问[：:])\s*', '', question).strip()
            if not q_clean:
                continue
            if re.search(r'[（(]打|打一', q_clean):
                continue

            if not href.startswith("http"):
                href = BASE_URL + (href if href.startswith("/") else "/" + href)

            h = generate_hash(q_clean, "")
            answer = extract_answer_from_detail(href)
            if not answer:
                continue

            page_entries.append((q_clean, answer))
            time.sleep(random.uniform(0.05, 0.2))

        if page_entries:
            added = insert_entries_batch(DB_PATH, page_entries, "brain_teaser", existing_hashes)
            total_added += added
            current = get_count(DB_PATH, "brain_teaser")
            print(f"  第 {page_num}/{max_page} 页: {len(page_entries)} 条, 新增 {added}, 总计 {current}/{TARGET}")

        time.sleep(random.uniform(0.2, 0.5))

    return total_added


def main():
    current = get_count(DB_PATH, "brain_teaser")
    print(f"当前脑筋急转弯: {current}/{TARGET}")
    if current >= TARGET:
        print("已达标!")
        return

    existing_hashes = get_existing_hashes(DB_PATH)
    print(f"已有 {len(existing_hashes)} 条去重哈希")

    sections = [
        ("/miyujingxuan/", "myjx36", 49, "谜语精选"),
        ("/mygs/", "list49", 9, "谜语故事"),
        ("/miyuku4/", "list_127_", 1741, "谜语库4"),
    ]

    for path, prefix, max_page, name in sections:
        current = get_count(DB_PATH, "brain_teaser")
        if current >= TARGET:
            break
        print(f"\n[{name}] 开始爬取 ({path}, {max_page} 页)")
        added = crawl_section(path, prefix, max_page, existing_hashes)
        print(f"[{name}] 新增 {added} 条")

    print(f"\n=== 最终统计 ===")
    print(f"脑筋急转弯: {get_count(DB_PATH, 'brain_teaser')}")
    print(f"谜语: {get_count(DB_PATH, 'riddle')}")


if __name__ == "__main__":
    main()
