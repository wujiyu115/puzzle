"""
应用配置
"""
import os
import logging

# 日志配置
LOG_LEVEL = logging.INFO
LOG_DIR = os.path.join(os.getcwd(), 'logs')

# 本地网络IP地址列表
# 支持以下格式：
# 1. 精确IP地址，如 '127.0.0.1'
# 2. 正则表达式模式，如 '^192\.168\.1\.\d+$'
LOCAL_NETWORK_IPS = [
    '127.0.0.1',  # localhost IPv4
    '::1',        # localhost IPv6
    # 添加更多本地网络IP地址或模式
    # 例如：
    # '^10\.\d+\.\d+\.\d+$',  # 10.x.x.x 网段
    # '^172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+$',  # 172.16.0.0 - 172.31.255.255 网段
    # '^192\.168\.\d+\.\d+$',  # 192.168.x.x 网段
]

# LLM服务配置
# 可以在环境变量中设置这些API密钥，或者在这里直接配置
# 注意：不建议将API密钥直接硬编码在代码中，建议使用环境变量
LLM_CONFIG = {
    # 是否启用LLM功能
    "ENABLED": True,
    # 默认模型
    "DEFAULT_MODEL": "deepseek-chat",
    # API密钥（优先使用环境变量）
    "API_KEYS": {
        "deepseek": "",  # 也可通过环境变量 DEEPSEEK_API_KEY 设置
        "openrouter": "",  # 也可通过环境变量 OPENROUTER_API_KEY 设置
        "qianwen": "",  # 也可通过环境变量 QIANWEN_API_KEY 设置
    },
    # 默认参数
    "DEFAULT_PARAMS": {"temperature": 0.7, "max_tokens": 1000, "top_p": 0.9},
}
