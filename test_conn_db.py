#!/usr/bin/env python
"""
SQLite数据库连接测试脚本

这个脚本用于测试SQLite数据库连接，检查数据库文件是否存在，
尝试连接数据库，并显示表结构和数据条目。
"""

import os
import sqlite3
import sys
from datetime import datetime

# 数据库文件路径
DB_PATH = os.path.join(os.getcwd(), 'data', 'puzzle_data.db')

def print_separator(title=None):
    """打印分隔线"""
    width = 80
    if title:
        print("\n" + "=" * 10 + f" {title} " + "=" * (width - len(title) - 12) + "\n")
    else:
        print("\n" + "=" * width + "\n")

def check_db_exists():
    """检查数据库文件是否存在"""
    print_separator("检查数据库文件")
    
    # 检查数据目录是否存在
    data_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(data_dir):
        print(f"数据目录不存在: {data_dir}")
        print(f"正在创建数据目录...")
        try:
            os.makedirs(data_dir)
            print(f"数据目录创建成功: {data_dir}")
        except Exception as e:
            print(f"创建数据目录失败: {str(e)}")
            return False
    
    # 检查数据库文件是否存在
    if os.path.exists(DB_PATH):
        file_size = os.path.getsize(DB_PATH)
        modified_time = datetime.fromtimestamp(os.path.getmtime(DB_PATH))
        print(f"数据库文件存在: {DB_PATH}")
        print(f"文件大小: {file_size} 字节")
        print(f"最后修改时间: {modified_time}")
        return True
    else:
        print(f"数据库文件不存在: {DB_PATH}")
        return False

def test_connection():
    """测试数据库连接"""
    print_separator("测试数据库连接")
    
    try:
        # 尝试连接数据库
        conn = sqlite3.connect("sqlite:///data/puzzle_data.db")
        cursor = conn.cursor()
        
        print("数据库连接成功!")
        
        # 获取SQLite版本
        cursor.execute("SELECT sqlite_version();")
        version = cursor.fetchone()
        print(f"SQLite版本: {version[0]}")
        
        return conn, cursor
    except sqlite3.Error as e:
        print(f"数据库连接失败: {str(e)}")
        return None, None

def get_table_info(conn, cursor):
    """获取表信息"""
    print_separator("数据库表信息")
    
    try:
        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("数据库中没有表")
            return
        
        print(f"数据库中的表 ({len(tables)}):")
        for i, table in enumerate(tables, 1):
            table_name = table[0]
            print(f"{i}. {table_name}")
            
            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            print(f"   表结构:")
            for col in columns:
                col_id, col_name, col_type, not_null, default_val, pk = col
                print(f"   - {col_name} ({col_type}){' PRIMARY KEY' if pk else ''}{' NOT NULL' if not_null else ''}")
            
            # 获取记录数
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"   记录数: {count}")
            
            # 显示前5条记录
            if count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5;")
                rows = cursor.fetchall()
                print(f"   前{min(5, count)}条记录:")
                
                # 获取列名
                column_names = [col[1] for col in columns]
                
                # 打印列名
                print("   | " + " | ".join(column_names) + " |")
                print("   | " + " | ".join(["-" * len(name) for name in column_names]) + " |")
                
                # 打印数据
                for row in rows:
                    print("   | " + " | ".join([str(val) for val in row]) + " |")
            
            print()
    except sqlite3.Error as e:
        print(f"获取表信息失败: {str(e)}")

def main():
    """主函数"""
    print("\nSQLite数据库连接测试")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"数据库路径: {DB_PATH}")
    
    # 检查数据库文件是否存在
    db_exists = check_db_exists()
    
    if not db_exists:
        create_db = input("数据库文件不存在，是否创建空数据库? (y/n): ")
        if create_db.lower() != 'y':
            print("测试结束")
            return
        
        try:
            # 创建数据目录（如果不存在）
            data_dir = os.path.dirname(DB_PATH)
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            
            # 创建空数据库
            conn = sqlite3.connect(DB_PATH)
            conn.close()
            print(f"空数据库创建成功: {DB_PATH}")
        except Exception as e:
            print(f"创建数据库失败: {str(e)}")
            return
    
    # 测试数据库连接
    conn, cursor = test_connection()
    if not conn or not cursor:
        print("无法连接到数据库，测试结束")
        return
    
    # 获取表信息
    get_table_info(conn, cursor)
    
    # 关闭连接
    cursor.close()
    conn.close()
    print("\n数据库连接已关闭")
    print("测试完成")

if __name__ == "__main__":
    main()
