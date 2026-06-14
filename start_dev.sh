#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt -q

# 复制环境变量文件（如果不存在）
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env from .env.example, please update it with your settings."
fi

# 初始化数据库
python init_db.py

# 启动开发服务器
export FLASK_ENV=development
python run.py
