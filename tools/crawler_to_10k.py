#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫脚本：从 cmiyu.com 爬取脑筋急转弯和谜语，直接写入 SQLite 数据库。
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
PROGRESS_FILE = os.path.join(SCRIPT_DIR, "crawler_progress.json")

BASE_URL = "http://www.cmiyu.com"
TARGET = 10000

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}



def generate_hash(question, answer):
    combined = f"{question}|{answer}"
    return hashlib.md5(combined.encode()).hexdigest()


def get_existing_hashes(db_path, category):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT content_hash FROM data_entries WHERE category=?", (category,))
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


SESSION = requests.Session()
SESSION.headers.update(HEADERS)


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
    """检测分页URL模式，从第一页的分页链接中提取。
    返回 (prefix, max_page)，其中 prefix 是页码前的固定字符串，
    实际URL = section_path + prefix + str(page_num) + ".html"
    """
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
        prefix = "my12"

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
            q_clean = re.sub(r'^(问[：:])\s*', '', question).strip()
            if not q_clean:
                continue

            answer = extract_answer_from_detail(detail_url)
            if not answer:
                continue

            content_hash = generate_hash(q_clean, answer)
            if content_hash in existing_hashes:
                continue

            page_entries.append((q_clean, answer))
            time.sleep(random.uniform(0.1, 0.3))

        if page_entries:
            added = insert_entries_batch(db_path, page_entries, category, existing_hashes)
            total_added += added
            current_count = get_count(db_path, category)
            print(f"  第 {page_num} 页: 获取 {len(page_entries)} 条, 新增 {added} 条, 总计 {current_count}/{TARGET}")
        else:
            print(f"  第 {page_num} 页: 无新数据")

        time.sleep(random.uniform(0.3, 0.8))

    print(f"[{category}] 本次新增 {total_added} 条, 当前总计 {get_count(db_path, category)} 条")


def main():
    if not os.path.exists(DB_PATH):
        print(f"数据库不存在: {DB_PATH}")
        sys.exit(1)

    # 爬取脑筋急转弯
    bt_count = get_count(DB_PATH, "brain_teaser")
    if bt_count < TARGET:
        bt_hashes = get_existing_hashes(DB_PATH, "brain_teaser")
        # 也加载谜语的hash避免跨类别重复
        all_hashes = bt_hashes | get_existing_hashes(DB_PATH, "riddle")
        crawl_section("/njmy/", "brain_teaser", DB_PATH, all_hashes)
    else:
        print(f"[brain_teaser] 已有 {bt_count} 条，已达标")

    # 爬取谜语
    r_count = get_count(DB_PATH, "riddle")
    if r_count < TARGET:
        r_hashes = get_existing_hashes(DB_PATH, "riddle")
        all_hashes = r_hashes | get_existing_hashes(DB_PATH, "brain_teaser")
        riddle_sections = [
            "/etmy/",   # 儿童谜语
            "/dwmy/",   # 动物谜语
            "/wpmy/",   # 物品谜语
            "/zwmy/",   # 植物谜语
            "/gxmy/",   # 搞笑谜语
            "/aqmy/",   # 爱情谜语
            "/cymy/",   # 成语谜语
            "/zmmy/",   # 字谜
            "/dmmy/",   # 灯谜
            "/qita/",   # 趣味谜语
        ]
        for section in riddle_sections:
            r_count = get_count(DB_PATH, "riddle")
            if r_count >= TARGET:
                print(f"[riddle] 已达到 {r_count} 条!")
                break
            crawl_section(section, "riddle", DB_PATH, all_hashes)
    else:
        print(f"[riddle] 已有 {r_count} 条，已达标")

    # 最终统计
    print("\n=== 最终统计 ===")
    print(f"脑筋急转弯: {get_count(DB_PATH, 'brain_teaser')} 条")
    print(f"谜语: {get_count(DB_PATH, 'riddle')} 条")


if __name__ == "__main__":
    main()
