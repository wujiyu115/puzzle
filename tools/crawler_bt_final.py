#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 cmiyu.com 谜语精选和谜语库4 爬取脑筋急转弯风格条目，写入 origin_data/brain_teaser.txt。
"""

import hashlib
import os
import re
import sys
import time
import random
import requests
from bs4 import BeautifulSoup
from clean_data import append_entries as write_entries

sys.stdout.reconfigure(line_buffering=True)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "origin_data", "brain_teaser.txt")
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


def append_entries_batch(entries, existing_hashes):
    added = write_entries(OUTPUT_PATH, entries, existing_hashes)
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


def crawl_section(section_path, prefix, max_page, existing_hashes, current_count):
    total_added = 0
    consecutive_empty = 0

    for page_num in range(1, max_page + 1):
        if current_count >= TARGET:
            print(f"  [DONE] 已达到 {current_count} 条!")
            return total_added, current_count

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

            answer = extract_answer_from_detail(href)
            if not answer:
                continue

            page_entries.append((q_clean, answer))
            time.sleep(random.uniform(0.05, 0.2))

        if page_entries:
            added = append_entries_batch(page_entries, existing_hashes)
            total_added += added
            current_count += added
            print(f"  第 {page_num}/{max_page} 页: {len(page_entries)} 条, 新增 {added}, 总计 {current_count}/{TARGET}")

        time.sleep(random.uniform(0.2, 0.5))

    return total_added, current_count


def main():
    existing_hashes, current_count = load_existing()
    print(f"当前脑筋急转弯: {current_count}/{TARGET}")
    if current_count >= TARGET:
        print("已达标!")
        return

    print(f"已有 {len(existing_hashes)} 条去重哈希")

    sections = [
        ("/miyujingxuan/", "myjx36", 49, "谜语精选"),
        ("/mygs/", "list49", 9, "谜语故事"),
        ("/miyuku4/", "list_127_", 1741, "谜语库4"),
    ]

    for path, prefix, max_page, name in sections:
        if current_count >= TARGET:
            break
        print(f"\n[{name}] 开始爬取 ({path}, {max_page} 页)")
        added, current_count = crawl_section(path, prefix, max_page, existing_hashes, current_count)
        print(f"[{name}] 新增 {added} 条")

    print(f"\n=== 最终统计 ===")
    print(f"脑筋急转弯: {current_count}")


if __name__ == "__main__":
    main()
