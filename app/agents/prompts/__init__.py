# -*- coding: utf-8 -*-
"""
Prompts 配置包。

提供统一的 prompt 加载和管理功能。
"""

from .loader import PromptLoader, get_prompt, get_config, get_prompt_loader

__all__ = [
    "PromptLoader",
    "get_prompt",
    "get_config",
    "get_prompt_loader",
]
