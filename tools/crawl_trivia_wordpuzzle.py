#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫脚本：从 cmiyu.com 爬取知识问答和字谜，直接写入 SQLite 数据库。
目标：每个分类达到 10,000 条。
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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def generate_hash(question, answer):
    combined = f"{question}|{answer}"
    return hashlib.md5(combined.encode()).hexdigest()


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
                print(f"  [WARN] 请求失败 {url}: {e}")
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


def detect_pagination_pattern(section_path):
    html = fetch_page(BASE_URL + section_path)
    if not html:
        return None, 0
    soup = BeautifulSoup(html, "html.parser")
    pages = soup.select("div.pages li")
    prefix = None
    max_page = 1
    for p in pages:
        a = p.select_one("a")
        if not a or not a.get("href"):
            continue
        href = a.get("href")
        text = p.get_text().strip()
        if text == "末页":
            m = re.search(r'(\d+)\.html', href)
            if m:
                max_page = int(m.group(1))
        if text == "2" and prefix is None:
            m = re.match(r'(.+?)2\.html$', href)
            if m:
                prefix = m.group(1)
    return prefix, max_page


def crawl_listing_page(url):
    html = fetch_page(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("div.list > ul > li")
    results = []
    for item in items:
        a = item.select_one("a")
        if not a:
            continue
        question = a.get_text().strip()
        href = a.get("href")
        if not question or not href:
            continue
        if not href.startswith("http"):
            href = BASE_URL + (href if href.startswith("/") else "/" + href)
        results.append((question, href))
    return results


def clean_question(question, category):
    """清理问题文本"""
    q = question.strip()
    if category == "word_puzzle":
        q = re.sub(r'\s*（打一字）\s*$', '', q)
        q = re.sub(r'\s*\(打一字\)\s*$', '', q)
    q = re.sub(r'^(问[：:])\s*', '', q)
    return q.strip()


def crawl_section(section_path, category, db_path, existing_hashes):
    current_count = get_count(db_path, category)
    if current_count >= TARGET:
        print(f"[{category}] 已达到 {current_count} 条，跳过")
        return

    print(f"\n[{category}] 当前 {current_count} 条，目标 {TARGET} 条")
    print(f"  检测分页模式: {section_path}")

    prefix, max_page = detect_pagination_pattern(section_path)
    if not prefix:
        print(f"  [WARN] 无法检测分页模式，使用默认模式")
        prefix = "my17"

    print(f"  分页前缀: {prefix}, 最大页数: {max_page}")

    total_added = 0
    consecutive_empty = 0

    for page_num in range(1, max_page + 1):
        current_count = get_count(db_path, category)
        if current_count >= TARGET:
            print(f"  [DONE] 已达到 {current_count} 条!")
            break

        if page_num == 1:
            page_url = BASE_URL + section_path
        else:
            page_url = f"{BASE_URL}{section_path}{prefix}{page_num}.html"

        items = crawl_listing_page(page_url)
        if not items:
            consecutive_empty += 1
            if consecutive_empty >= 5:
                print(f"  连续 {consecutive_empty} 页为空，停止此分类")
                break
            continue

        consecutive_empty = 0
        page_entries = []

        for question, detail_url in items:
            q_clean = clean_question(question, category)
            if not q_clean:
                continue

            answer = extract_answer_from_detail(detail_url)
            if not answer:
                continue

            content_hash = generate_hash(q_clean, answer)
            if content_hash in existing_hashes:
                continue

            page_entries.append((q_clean, answer))
            time.sleep(random.uniform(0.05, 0.15))

        if page_entries:
            added = insert_entries_batch(db_path, page_entries, category, existing_hashes)
            total_added += added
            current_count = get_count(db_path, category)
            print(f"  第 {page_num}/{max_page} 页: 获取 {len(page_entries)} 条, 新增 {added} 条, 总计 {current_count}/{TARGET}")
        else:
            if page_num % 50 == 0:
                print(f"  第 {page_num}/{max_page} 页: 无新数据")

        time.sleep(random.uniform(0.1, 0.3))

    print(f"[{category}] 本次新增 {total_added} 条, 当前总计 {get_count(db_path, category)} 条")


def main():
    if not os.path.exists(DB_PATH):
        print(f"数据库不存在: {DB_PATH}")
        sys.exit(1)

    # 加载所有已有的 hash，跨类别去重
    all_hashes = get_all_hashes(DB_PATH)
    print(f"已有 {len(all_hashes)} 个唯一条目")

    # 爬取知识问答 (trivia)
    t_count = get_count(DB_PATH, "trivia")
    if t_count < TARGET:
        crawl_section("/zlmy/", "trivia", DB_PATH, all_hashes)
    else:
        print(f"[trivia] 已有 {t_count} 条，已达标")

    # 爬取字谜 (word_puzzle)
    w_count = get_count(DB_PATH, "word_puzzle")
    if w_count < TARGET:
        crawl_section("/zmmy/", "word_puzzle", DB_PATH, all_hashes)
    else:
        print(f"[word_puzzle] 已有 {w_count} 条，已达标")

    # 最终统计
    print("\n=== 最终统计 ===")
    print(f"知识问答: {get_count(DB_PATH, 'trivia')} 条")
    print(f"字谜: {get_count(DB_PATH, 'word_puzzle')} 条")


if __name__ == "__main__":
    main()
