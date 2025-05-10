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
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "origin_data", "riddle.txt")

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
            # 确保是完整URL
            if not href.startswith("http"):
                href = BASE_URL + href
            if href != ETMY_URL:
                urls.append(href)
    
    return urls


def extract_riddles_from_page(url):
    """
    从页面中提取谜语数据
    """
    content = get_page_content(url)
    # print(content)  # Debug: print the content to check if it

    if not content:
        return []
    
    soup = BeautifulSoup(content, "html.parser")
    riddles = []
    
    # 查找谜面和谜底
    # 尝试多种模式匹配谜语
    text = soup.get_text()
    
    # 模式1：标准的谜面谜底格式
    pattern1 = r"谜面：(.+?)\s+谜底：(.+?)(?:\s+|$)"
    matches1 = re.findall(pattern1, text, re.DOTALL)
    # print(matches1)
    
    # 模式2：简单的问答格式
    pattern2 = r"([^\n]+?)\s*（打[一二三四五六七八九十]\w+）\s*([^\n]+?)(?:\s+|$)"
    matches2 = re.findall(pattern2, text, re.DOTALL)
    # print(matches2)
    
    # 处理模式1的匹配结果
    for match in matches1:
        question = match[0].strip()
        answer = match[1].strip()
        
        # 过滤掉小贴士和其他非谜底内容
        if "小贴士" in answer:
            answer = answer.split("小贴士")[0].strip()
        
        # 确保问题和答案都不为空
        if question and answer:
            riddles.append({
                "question": question,
                "answer": answer
            })
    
    # 处理模式2的匹配结果
    for match in matches2:
        question = match[0].strip()
        answer = match[1].strip()
        
        # 确保问题和答案都不为空
        if question and answer:
            # 添加"打一XX"到问题中
            if "打一" not in question and "（打" in question:
                parts = question.split("（")
                if len(parts) > 1:
                    question = parts[0].strip()
            
            riddles.append({
                "question": question,
                "answer": answer
            })
    
    return riddles


def format_riddle(riddle):
    """
    格式化谜语为指定格式
    """
    return f"问题：{riddle['question']}\n答案:{riddle['answer']}"


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
    print("开始爬取谜语数据...")
    
    # 获取谜语页面URL列表
    page_urls = get_riddle_page_urls()
    if not page_urls:
        print("未找到谜语页面，请检查网站结构是否变化")
        return
    
    print(f"找到 {len(page_urls)} 个谜语页面")
    
    # 爬取谜语数据
    all_riddles = []
    for i, url in enumerate(page_urls):
        print(f"正在爬取第 {i+1}/{len(page_urls)} 个页面: {url}")
        riddles = extract_riddles_from_page(url)
        all_riddles.extend(riddles)
        
        # 随机延时，避免请求过于频繁
        time.sleep(random.uniform(1, 3))
    
    print(f"共爬取到 {len(all_riddles)} 条谜语")
    
    # 移除重复的谜语
    unique_riddles = remove_duplicates(all_riddles)
    print(f"去重后剩余 {len(unique_riddles)} 条谜语")
    
    # 保存谜语到文件
    if unique_riddles:
        save_riddles_to_file(unique_riddles)
        print("谜语数据爬取完成！")
    else:
        print("没有新的谜语数据需要保存")


if __name__ == "__main__":
    main()