"""
LLM服务模块 - 提供对多种大型语言模型的访问

支持的模型:
- DeepSeek
- OpenRouter
- 千问(Qianwen)
"""

import os
import json
import requests
from typing import Dict, Any, Optional, List, Union

# 默认参数
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1000
DEFAULT_TOP_P = 0.9

class LLMServiceError(Exception):
    """LLM服务错误基类"""
    pass

class AuthenticationError(LLMServiceError):
    """认证错误"""
    pass

class APIError(LLMServiceError):
    """API调用错误"""
    pass

class ModelNotSupportedError(LLMServiceError):
    """模型不支持错误"""
    pass

class LLMService:
    """LLM服务类，提供对多种大型语言模型的统一访问接口"""
    
    def __init__(self, api_keys: Dict[str, str] = None):
        """
        初始化LLM服务
        
        Args:
            api_keys: 包含各服务API密钥的字典，格式为 {'service_name': 'api_key'}
        """
        self.api_keys = api_keys or {}
        
        # 从环境变量加载API密钥（如果未提供）
        if 'deepseek' not in self.api_keys and os.environ.get('DEEPSEEK_API_KEY'):
            self.api_keys['deepseek'] = os.environ.get('DEEPSEEK_API_KEY')
            
        if 'openrouter' not in self.api_keys and os.environ.get('OPENROUTER_API_KEY'):
            self.api_keys['openrouter'] = os.environ.get('OPENROUTER_API_KEY')
            
        if 'qianwen' not in self.api_keys and os.environ.get('QIANWEN_API_KEY'):
            self.api_keys['qianwen'] = os.environ.get('QIANWEN_API_KEY')
    
    def _check_api_key(self, service: str) -> str:
        """检查API密钥是否存在"""
        if service not in self.api_keys or not self.api_keys[service]:
            raise AuthenticationError(f"未提供{service}的API密钥")
        return self.api_keys[service]
    
    def chat_completion(self, 
                        messages: List[Dict[str, str]], 
                        model: str = "deepseek-chat", 
                        temperature: float = DEFAULT_TEMPERATURE,
                        max_tokens: int = DEFAULT_MAX_TOKENS,
                        top_p: float = DEFAULT_TOP_P,
                        stream: bool = False) -> Dict[str, Any]:
        """
        统一的聊天完成接口
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "你好"}]
            model: 模型名称，支持 deepseek-chat, openrouter:xxx, qianwen-xxx
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            top_p: top-p采样参数
            stream: 是否使用流式响应
            
        Returns:
            包含生成内容的字典
        """
        # 根据模型名称确定使用哪个服务
        if model.startswith("deepseek"):
            return self._deepseek_chat_completion(messages, model, temperature, max_tokens, top_p, stream)
        elif model.startswith("openrouter:"):
            # 从openrouter:model-name格式中提取实际模型名称
            actual_model = model.split(":", 1)[1]
            return self._openrouter_chat_completion(messages, actual_model, temperature, max_tokens, top_p, stream)
        elif model.startswith("qianwen"):
            return self._qianwen_chat_completion(messages, model, temperature, max_tokens, top_p, stream)
        else:
            raise ModelNotSupportedError(f"不支持的模型: {model}")
    
    def _deepseek_chat_completion(self, 
                                 messages: List[Dict[str, str]], 
                                 model: str = "deepseek-chat", 
                                 temperature: float = DEFAULT_TEMPERATURE,
                                 max_tokens: int = DEFAULT_MAX_TOKENS,
                                 top_p: float = DEFAULT_TOP_P,
                                 stream: bool = False) -> Dict[str, Any]:
        """
        调用DeepSeek API进行聊天完成
        
        Args:
            messages: 消息列表
            model: 模型名称，如 deepseek-chat
            temperature: 温度参数
            max_tokens: 最大生成token数
            top_p: top-p采样参数
            stream: 是否使用流式响应
            
        Returns:
            包含生成内容的字典
        """
        api_key = self._check_api_key('deepseek')
        
        # DeepSeek API端点
        api_url = "https://api.deepseek.com/v1/chat/completions"
        
        # 准备请求数据
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": stream
        }
        
        # 设置请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        try:
            response = requests.post(api_url, json=payload, headers=headers)
            response.raise_for_status()  # 如果响应状态码不是200，抛出异常
            return response.json()
        except requests.exceptions.RequestException as e:
            raise APIError(f"DeepSeek API调用失败: {str(e)}")
    
    def _openrouter_chat_completion(self, 
                                   messages: List[Dict[str, str]], 
                                   model: str, 
                                   temperature: float = DEFAULT_TEMPERATURE,
                                   max_tokens: int = DEFAULT_MAX_TOKENS,
                                   top_p: float = DEFAULT_TOP_P,
                                   stream: bool = False) -> Dict[str, Any]:
        """
        调用OpenRouter API进行聊天完成
        
        Args:
            messages: 消息列表
            model: 模型名称，如 anthropic/claude-3-opus
            temperature: 温度参数
            max_tokens: 最大生成token数
            top_p: top-p采样参数
            stream: 是否使用流式响应
            
        Returns:
            包含生成内容的字典
        """
        api_key = self._check_api_key('openrouter')
        
        # OpenRouter API端点
        api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        # 准备请求数据
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": stream
        }
        
        # 设置请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://puzzle-app.local",  # OpenRouter需要提供referer
            "X-Title": "Puzzle App"  # 应用名称
        }
        
        try:
            response = requests.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise APIError(f"OpenRouter API调用失败: {str(e)}")
    
    def _qianwen_chat_completion(self, 
                                messages: List[Dict[str, str]], 
                                model: str = "qianwen-max", 
                                temperature: float = DEFAULT_TEMPERATURE,
                                max_tokens: int = DEFAULT_MAX_TOKENS,
                                top_p: float = DEFAULT_TOP_P,
                                stream: bool = False) -> Dict[str, Any]:
        """
        调用阿里云千问(Qianwen) API进行聊天完成
        
        Args:
            messages: 消息列表
            model: 模型名称，如 qianwen-max, qianwen-plus
            temperature: 温度参数
            max_tokens: 最大生成token数
            top_p: top-p采样参数
            stream: 是否使用流式响应
            
        Returns:
            包含生成内容的字典
        """
        api_key = self._check_api_key('qianwen')
        
        # 千问API端点
        api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        
        # 千问API使用不同的模型名称映射
        model_mapping = {
            "qianwen-max": "qwen-max",
            "qianwen-plus": "qwen-plus",
            "qianwen-turbo": "qwen-turbo"
        }
        
        actual_model = model_mapping.get(model, model)
        
        # 准备请求数据 - 千问API格式与OpenAI格式略有不同
        payload = {
            "model": actual_model,
            "input": {
                "messages": messages
            },
            "parameters": {
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
                "result_format": "message",
                "stream": stream
            }
        }
        
        # 设置请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        try:
            response = requests.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            
            # 千问API响应格式转换为OpenAI格式
            qianwen_response = response.json()
            
            # 转换为统一格式
            if "output" in qianwen_response and "message" in qianwen_response["output"]:
                return {
                    "choices": [
                        {
                            "message": qianwen_response["output"]["message"],
                            "finish_reason": qianwen_response["output"].get("finish_reason", "stop")
                        }
                    ],
                    "model": actual_model,
                    "usage": qianwen_response.get("usage", {})
                }
            return qianwen_response
        except requests.exceptions.RequestException as e:
            raise APIError(f"千问API调用失败: {str(e)}")

    def get_available_models(self) -> Dict[str, List[str]]:
        """
        获取可用的模型列表
        
        Returns:
            按服务分组的可用模型字典
        """
        models = {
            "deepseek": [
                "deepseek-chat",
                "deepseek-coder"
            ],
            "openrouter": [
                "openrouter:anthropic/claude-3-opus",
                "openrouter:anthropic/claude-3-sonnet",
                "openrouter:anthropic/claude-3-haiku",
                "openrouter:openai/gpt-4o",
                "openrouter:openai/gpt-4-turbo",
                "openrouter:google/gemini-pro"
            ],
            "qianwen": [
                "qianwen-max",
                "qianwen-plus",
                "qianwen-turbo"
            ]
        }
        
        # 只返回有API密钥的服务的模型
        return {service: model_list for service, model_list in models.items() if service in self.api_keys}

# 创建一个默认实例
default_llm_service = LLMService()

def chat_completion(messages, model="deepseek-chat", **kwargs):
    """便捷函数，使用默认服务实例进行聊天完成"""
    return default_llm_service.chat_completion(messages, model, **kwargs)

def get_available_models():
    """便捷函数，获取可用模型列表"""
    return default_llm_service.get_available_models()
