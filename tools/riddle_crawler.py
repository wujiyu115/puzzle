#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
谜语爬虫脚本

从 http://www.cmiyu.com/etmy/ 网站爬取儿童谜语数据，
并按照指定格式追加到 origin_data/riddle.txt 文件中
"""

import os
import re
import time
import random
import requests
from bs4 import BeautifulSoup

# 配置
BASE_URL = "http://www.cmiyu.com"
ETMY_URL = f"{BASE_URL}/etmy/"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "origin_data", "riddle.txt")
VISITED_URLS_FILE = os.path.join(SCRIPT_DIR, "visited_urls.txt")


def join_url(base, path):
    """
    正确拼接URL，避免出现域名和路径直接连接的问题
    """
    if not path:
        return base
    
    # 如果是完整URL，直接返回
    if path.startswith('http'):
        return path
    
    # 确保base不以/结尾，path以/开头
    base = base.rstrip('/')
    if not path.startswith('/'):
        path = '/' + path
    
    return base + path

# 请求头，模拟浏览器访问
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def get_page_content(url):
    """
    获取页面内容
    """
    try:
        print(f"正在请求: {url}")
        # 验证URL格式
        if not url.startswith('http'):
            print(f"无效的URL格式: {url}")
            return None
            
        response = requests.get(url, headers=HEADERS, timeout=10)
        # 尝试多种编码方式，解决乱码问题
        # 先尝试自动检测
        if response.status_code == 200:
            # 先尝试 GB2312/GBK 编码（常见的中文编码）
            response.encoding = "gb18030"  # GB18030 是 GBK 的超集，兼容性更好
            content = response.text
            
            # 如果仍有乱码，可以尝试其他编码
            if "乱码" in content or "�" in content:
                response.encoding = "utf-8"
                content = response.text
            
            return content
        else:
            print(f"请求失败，状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"请求异常: {e}")
        return None


def get_riddle_page_urls():
    """
    获取儿童谜语页面的URL列表
    """
    content = get_page_content(ETMY_URL)
    if not content:
        return []
    
    soup = BeautifulSoup(content, "html.parser")
    urls = []
    
    # 查找所有可能的谜语页面链接
    for link in soup.find_all("a"):
        href = link.get("href")
        if href and "/etmy/" in href and href != ETMY_URL:
            # 使用join_url函数确保URL正确拼接
            full_url = join_url(BASE_URL, href)
            if full_url != ETMY_URL:
                urls.append(full_url)
    
    # 查找分页链接
    next_page = soup.select_one('li.sy3 > a:-soup-contains("下一页")')
    if next_page and next_page.get('href'):
        # 使用join_url函数确保URL正确拼接
        next_url = join_url(BASE_URL, next_page.get('href'))
        urls.append(next_url)
    
    return urls


def extract_riddles_from_page(url, visited_urls):
    """
    从页面中提取谜语数据，使用XPath选择器
    """
    if url in visited_urls:
        print(f"已访问过: {url}, 跳过")
        return []
    
    content = get_page_content(url)
    if not content:
        return []
    visited_urls.add(url) # 标记为已访问
    
    soup = BeautifulSoup(content, "html.parser")
    riddles = []
    
    # 使用XPath风格的选择器提取谜语列表
    miyu_list = soup.select('div.list > ul > li')
    
    for miyu in miyu_list:
        # 提取谜面（问题）
        question_elem = miyu.select_one('a')
        if question_elem:
            question = question_elem.get_text().strip()
        else:
            question_elem = miyu.select_one('a > b')
            if question_elem:
                question = question_elem.get_text().strip()
            else:
                continue
        
        # 获取详情页链接
        info_page = miyu.select_one('a')
        if info_page and info_page.get('href'):
            # 访问详情页获取谜底
            href = info_page.get('href')
            # 使用join_url函数确保URL正确拼接
            detail_url = join_url(BASE_URL, href)
            
            if detail_url in visited_urls:
                print(f"详情页已访问过: {detail_url}, 跳过")
                continue # 跳过这个谜语，因为详情页已处理
            
            detail_content = get_page_content(detail_url)
            if detail_content:
                visited_urls.add(detail_url) # 标记详情页为已访问
            
            if detail_content:
                detail_soup = BeautifulSoup(detail_content, "html.parser")
                
                # 提取谜底（答案）
                answer_elem = detail_soup.select_one('div.md > h3:nth-of-type(2)')
                if answer_elem:
                    answer = answer_elem.get_text().replace('谜底：', '').strip()
                    
                    # 提取注释（如果有）
                    annotation_elem = detail_soup.select_one('div.zy > p')
                    annotation = ''
                    if annotation_elem:
                        annotation = annotation_elem.get_text().strip()
                    
                    # 确保问题和答案都不为空
                    if question and answer:
                        riddle = {
                            "question": question,
                            "answer": answer
                        }
                        
                        # 如果有注释，添加到谜语数据中
                        if annotation:
                            riddle["annotation"] = annotation
                            
                        riddles.append(riddle)
    
    # 处理分页
    next_page = soup.select_one('li.sy3 > a:-soup-contains("下一页")')
    if next_page and next_page.get('href'):
        # 使用join_url函数确保URL正确拼接
        next_url = join_url(BASE_URL, next_page.get('href'))
        # 递归获取下一页的谜语
        try:
            next_riddles = extract_riddles_from_page(next_url, visited_urls)
            riddles.extend(next_riddles)
        except Exception as e:
            print(f"获取下一页谜语失败: {next_url}, 错误: {e}")
    
    return riddles


def format_riddle(riddle):
    """
    格式化谜语为指定格式
    """
    formatted = f"问题：{riddle['question']}\n答案:{riddle['answer']}"
    
    # 如果有注释，添加到格式化的谜语中
    if 'annotation' in riddle and riddle['annotation']:
        formatted += f"\n注释:{riddle['annotation']}"
    
    return formatted


def save_riddles_to_file(riddles):
    """
    将谜语保存到文件
    """
    # 检查文件是否存在，如果不存在则创建
    if not os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("")
    
    # 读取现有内容，检查是否有结尾的空行
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 准备写入新内容
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        # 如果文件不为空且最后没有空行，先添加分隔符
        if content and not content.endswith("\n\n"):
            if content.endswith("\n"):
                f.write("---\n")
            else:
                f.write("\n---\n")
        
        # 写入谜语
        for i, riddle in enumerate(riddles):
            f.write(format_riddle(riddle))
            # 如果不是最后一个谜语，添加分隔符
            if i < len(riddles) - 1:
                f.write("\n---\n")
            else:
                f.write("\n")
    
    print(f"成功保存 {len(riddles)} 条谜语到 {OUTPUT_FILE}")


def remove_duplicates(riddles):
    """
    移除重复的谜语
    """
    # 读取现有文件内容
    existing_riddles = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            # 分割每个谜语
            parts = content.split("---")
            for part in parts:
                part = part.strip()
                if part:
                    # 提取问题和答案
                    lines = part.split("\n")
                    if len(lines) >= 2 and lines[0].startswith("问题：") and lines[1].startswith("答案:"):
                        question = lines[0][3:].strip()
                        answer = lines[1][3:].strip()
                        existing_riddles.add((question, answer))
    
    # 过滤掉重复的谜语
    unique_riddles = []
    for riddle in riddles:
        if (riddle["question"], riddle["answer"]) not in existing_riddles:
            unique_riddles.append(riddle)
            existing_riddles.add((riddle["question"], riddle["answer"]))
    
    return unique_riddles


def main():
    """
    主函数
    """
    print("开始爬取儿童谜语数据...")
    
    visited_urls = set()
    # 加载已访问的URL
    if os.path.exists(VISITED_URLS_FILE):
        with open(VISITED_URLS_FILE, "r", encoding="utf-8") as f:
            visited_urls = set(line.strip() for line in f)
        print(f"从 {VISITED_URLS_FILE} 加载了 {len(visited_urls)} 个已访问的URL")

    try:
        # 直接从主页开始爬取
        print(f"开始从 {ETMY_URL} 爬取谜语数据")
        all_riddles = extract_riddles_from_page(ETMY_URL, visited_urls)
        
        if not all_riddles:
            print("未能爬取到任何谜语数据，请检查网络连接或网站结构是否发生变化")
            return
        
        print(f"共爬取到 {len(all_riddles)} 条谜语")
        
        # 移除重复的谜语
        unique_riddles = remove_duplicates(all_riddles)
        print(f"去重后剩余 {len(unique_riddles)} 条谜语")
        
        # 保存谜语到文件
        if unique_riddles:
            save_riddles_to_file(unique_riddles)
            print("儿童谜语数据爬取完成！")
        else:
            print("没有新的谜语数据需要保存")
    except Exception as e:
        print(f"爬取过程中发生错误: {e}")
        print("请检查网络连接或网站结构是否发生变化")
    finally:
        # 保存已访问的URL
        with open(VISITED_URLS_FILE, "w", encoding="utf-8") as f:
            for url in visited_urls:
                f.write(url + "\n")
        print(f"已将 {len(visited_urls)} 个已访问的URL保存到 {VISITED_URLS_FILE}")
        
        # 如果有部分数据已爬取，尝试保存
        if 'all_riddles' in locals() and all_riddles:
            print(f"尝试保存已爬取的 {len(all_riddles)} 条谜语数据...")
            try:
                unique_riddles = remove_duplicates(all_riddles)
                if unique_riddles:
                    save_riddles_to_file(unique_riddles)
                    print(f"成功保存 {len(unique_riddles)} 条谜语数据")
            except Exception as save_error:
                print(f"保存数据时发生错误: {save_error}")
                print("无法保存已爬取的数据")


if __name__ == "__main__":
    main()