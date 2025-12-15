"""
LLM配置管理模块。
从环境变量加载API密钥和设置。
"""
import os
from typing import Dict, List, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


def get_config_list() -> List[Dict[str, Any]]:
    """
    从环境变量获取LLM配置列表。
    
    返回:
        LLM配置字典列表。
    """
    return [
        {
            "model": os.getenv('LLM_MODEL', 'deepseek-ai/DeepSeek-V3'),
            "api_key": os.getenv('LLM_API_KEY', ''),
            "base_url": os.getenv('LLM_BASE_URL', 'https://api.siliconflow.cn/v1'),
            "temperature": float(os.getenv('LLM_TEMPERATURE', '0')),
        }
    ]


def get_llm_config() -> Dict[str, Any]:
    """
    获取autogen代理的LLM配置。
    
    返回:
        autogen的配置字典。
    """
    return {
        "config_list": get_config_list(),
        "seed": 42,
        "timeout": int(os.getenv('LLM_TIMEOUT', '120')),
        "temperature": float(os.getenv('LLM_TEMPERATURE', '0')),
    }


def validate_llm_config() -> bool:
    """
    验证LLM配置是否正确设置。
    
    返回:
        如果配置有效则返回True，否则返回False。
    """
    api_key = os.getenv('LLM_API_KEY', '')
    if not api_key or api_key == 'your-api-key-here':
        return False
    return True


def get_llm_status() -> Dict[str, Any]:
    """
    获取当前 LLM配置状态。
    
    返回:
        包含配置信息的状态字典。
    """
    config = get_config_list()[0]
    return {
        "model": config["model"],
        "base_url": config["base_url"],
        "api_key_configured": bool(config["api_key"]) and config["api_key"] != 'your-api-key-here',
        "temperature": config["temperature"],
    }


def get_embedding_config() -> Dict[str, Any]:
    """
    获取Embedding模型配置。
    
    返回:
        Embedding配置字典。
    """
    llm_api_key = os.getenv('LLM_API_KEY', '')
    llm_base_url = os.getenv('LLM_BASE_URL', 'https://api.siliconflow.cn/v1')
    
    return {
        "model": os.getenv('EMBEDDING_MODEL', ''),
        "api_key": os.getenv('EMBEDDING_API_KEY') or llm_api_key,
        "base_url": os.getenv('EMBEDDING_BASE_URL') or llm_base_url,
    }
