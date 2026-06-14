#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 yjbys.com 的脑筋急转弯文章中提取 Q&A 对，写入 origin_data/brain_teaser.txt。
"""

import hashlib
import os
import re
import sys
import time
import random
import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(line_buffering=True)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "origin_data", "brain_teaser.txt")
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


def append_entries_batch(entries, existing_hashes):
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
    existing_hashes, current_count = load_existing()
    print(f"当前脑筋急转弯: {current_count}/{TARGET}")
    print(f"已有 {len(existing_hashes)} 条去重哈希")

    print("收集文章链接...")
    links = collect_article_links()
    print(f"找到 {len(links)} 篇文章")

    total_added = 0
    for i, url in enumerate(links):
        if current_count >= TARGET:
            print(f"[DONE] 已达到 {current_count} 条!")
            break

        pairs = extract_qa_from_article(url)
        if pairs:
            added = append_entries_batch(pairs, existing_hashes)
            total_added += added
            current_count += added
            print(f"  [{i+1}/{len(links)}] {url.split('/')[-1]}: {len(pairs)} 条, 新增 {added}, 总计 {current_count}/{TARGET}")

        time.sleep(random.uniform(0.5, 1.5))

    print(f"\nyjbys.com 新增 {total_added} 条")
    print(f"脑筋急转弯: {current_count}")


if __name__ == "__main__":
    main()
