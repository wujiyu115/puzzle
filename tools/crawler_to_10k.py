#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫脚本：从 cmiyu.com 爬取脑筋急转弯和谜语，写入 origin_data/ 的 txt 文件。
目标：每个分类达到 10,000 条。
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

BASE_URL = "http://www.cmiyu.com"
TARGET = 10000

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def get_output_path(category):
    return os.path.join(PROJECT_ROOT, "origin_data", f"{category}.txt")


def generate_hash(question, answer):
    combined = f"{question}|{answer}"
    return hashlib.md5(combined.encode()).hexdigest()


def sanitize(text):
    return text.replace("---", "——").replace("--", "——").strip()


def load_existing(category):
    filepath = get_output_path(category)
    hashes = set()
    count = 0
    if not os.path.exists(filepath):
        return hashes, count
    with open(filepath, "r", encoding="utf-8") as f:
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


def append_entries_batch(entries, category, existing_hashes):
    filepath = get_output_path(category)
    added = 0
    with open(filepath, "a", encoding="utf-8") as f:
        for q, a in entries:
            q, a = sanitize(q), sanitize(a)
            h = generate_hash(q, a)
            if h in existing_hashes:
                continue
            existing_hashes.add(h)
            f.write(f"问题：{q}\n答案:{a}\n---\n")
            added += 1
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


def crawl_section(section_path, category, existing_hashes, current_count):
    if current_count >= TARGET:
        print(f"[{category}] 已达到 {current_count} 条，跳过")
        return current_count

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
            added = append_entries_batch(page_entries, category, existing_hashes)
            total_added += added
            current_count += added
            print(f"  第 {page_num} 页: 获取 {len(page_entries)} 条, 新增 {added} 条, 总计 {current_count}/{TARGET}")
        else:
            print(f"  第 {page_num} 页: 无新数据")

        time.sleep(random.uniform(0.3, 0.8))

    print(f"[{category}] 本次新增 {total_added} 条, 当前总计 {current_count} 条")
    return current_count


def main():
    # 爬取脑筋急转弯
    bt_hashes, bt_count = load_existing("brain_teaser")
    if bt_count < TARGET:
        # 也加载谜语的hash避免跨类别重复
        r_hashes, _ = load_existing("riddle")
        all_hashes = bt_hashes | r_hashes
        bt_count = crawl_section("/njmy/", "brain_teaser", all_hashes, bt_count)
    else:
        print(f"[brain_teaser] 已有 {bt_count} 条，已达标")

    # 爬取谜语
    r_hashes, r_count = load_existing("riddle")
    if r_count < TARGET:
        all_hashes = r_hashes | bt_hashes
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
            if r_count >= TARGET:
                print(f"[riddle] 已达到 {r_count} 条!")
                break
            r_count = crawl_section(section, "riddle", all_hashes, r_count)
    else:
        print(f"[riddle] 已有 {r_count} 条，已达标")

    # 最终统计
    print("\n=== 最终统计 ===")
    print(f"脑筋急转弯: {bt_count} 条")
    print(f"谜语: {r_count} 条")


if __name__ == "__main__":
    main()
