"""
LLM 配置兼容模块。

此模块提供对旧 API 的兼容，所有功能委托给 LLMClient。
新代码应直接使用 llm_client.py 中的 get_llm_client()。
"""
from typing import Dict, List, Any

from .llm_client import get_llm_client
from app.core.config import settings


def get_llm_config() -> Dict[str, Any]:
    """获取 autogen 代理的 LLM 配置"""
    return get_llm_client().get_autogen_config()


def get_config_list() -> List[Dict[str, Any]]:
    """获取 LLM 配置列表"""
    return get_llm_client().get_autogen_config()["config_list"]


def validate_llm_config() -> bool:
    """验证 LLM 配置是否有效"""
    return get_llm_client().is_configured()


def get_llm_status() -> Dict[str, Any]:
    """获取当前 LLM 配置状态"""
    return get_llm_client().get_status()


def get_embedding_config() -> Dict[str, Any]:
    """获取 Embedding 模型配置"""
    return {
        "model": settings.embedding_model if hasattr(settings, 'embedding_model') else '',
        "api_key": settings.embedding_api_key if hasattr(settings, 'embedding_api_key') else settings.llm_api_key,
        "base_url": settings.embedding_base_url if hasattr(settings, 'embedding_base_url') else settings.llm_base_url,
    }
