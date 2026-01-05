# -*- coding: utf-8 -*-
"""
Prompt 加载器模块。

提供 YAML 格式 prompt 配置的加载、缓存和模板变量替换功能。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from loguru import logger


class PromptLoader:
    """
    Prompt 配置加载器。
    
    支持：
    - YAML 配置文件加载
    - 模板变量替换（{variable} 语法）
    - 内置缓存机制
    - 可选热加载（开发模式）
    """

    def __init__(self, base_path: Path | str | None = None, hot_reload: bool = False):
        """
        初始化加载器。
        
        Args:
            base_path: YAML 文件所在目录，默认为当前模块目录
            hot_reload: 是否启用热加载（每次都重新读取文件）
        """
        if base_path is None:
            base_path = Path(__file__).parent
        self.base_path = Path(base_path)
        self.hot_reload = hot_reload
        self._cache: Dict[str, Dict[str, Any]] = {}

    def load(self, name: str) -> Dict[str, Any]:
        """
        加载指定名称的 YAML 配置。
        
        Args:
            name: 配置文件名（不含 .yaml 后缀）
            
        Returns:
            解析后的配置字典
            
        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: YAML 解析失败
        """
        # 热加载模式下跳过缓存
        if not self.hot_reload and name in self._cache:
            return self._cache[name]

        file_path = self.base_path / f"{name}.yaml"
        if not file_path.exists():
            raise FileNotFoundError(f"Prompt 配置文件不存在: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self._cache[name] = data
            return data
        except yaml.YAMLError as e:
            logger.error("解析 YAML 失败 {}: {}", file_path, e)
            raise

    def get(self, name: str, key: str, **kwargs) -> str:
        """
        获取指定的 prompt 并进行变量替换。
        
        Args:
            name: 配置文件名（不含 .yaml 后缀）
            key: prompt 的键名（支持点号分隔的嵌套键，如 "system_prompts.interview"）
            **kwargs: 模板变量的值
            
        Returns:
            格式化后的 prompt 字符串
            
        Raises:
            KeyError: 指定的 key 不存在
        """
        data = self.load(name)
        
        # 支持点号分隔的嵌套键
        value = data
        for part in key.split("."):
            if not isinstance(value, dict):
                raise KeyError(f"无法在 {name} 中访问 '{key}': 中间值不是字典")
            if part not in value:
                raise KeyError(f"Prompt 键不存在: {name}.{key}")
            value = value[part]

        if not isinstance(value, str):
            raise TypeError(f"期望字符串类型的 prompt，但 {name}.{key} 是 {type(value).__name__}")

        # 模板变量替换
        if kwargs:
            try:
                return value.format(**kwargs)
            except KeyError as e:
                logger.warning("Prompt 模板变量缺失: {} in {}.{}", e, name, key)
                return value
        return value

    def get_config(self, name: str, key: str | None = None) -> Any:
        """
        获取配置值（非 prompt 的配置项）。
        
        Args:
            name: 配置文件名
            key: 配置键名，None 则返回整个配置
            
        Returns:
            配置值
        """
        data = self.load(name)
        
        if key is None:
            return data
            
        # 支持点号分隔的嵌套键
        value = data
        for part in key.split("."):
            if not isinstance(value, dict):
                raise KeyError(f"无法在 {name} 中访问 '{key}'")
            if part not in value:
                raise KeyError(f"配置键不存在: {name}.{key}")
            value = value[part]
        return value

    def clear_cache(self) -> None:
        """清除缓存。"""
        self._cache.clear()
        logger.debug("Prompt 缓存已清除")


# ========== 全局单例和便捷函数 ==========

_loader: PromptLoader | None = None


def get_prompt_loader(hot_reload: bool | None = None) -> PromptLoader:
    """
    获取全局 PromptLoader 单例。
    
    Args:
        hot_reload: 是否启用热加载，None 则根据环境变量决定
        
    Returns:
        PromptLoader 实例
    """
    global _loader
    if _loader is None:
        if hot_reload is None:
            # 开发环境默认启用热加载
            hot_reload = os.getenv("APP_ENV", "development") == "development"
        _loader = PromptLoader(hot_reload=hot_reload)
    return _loader


def get_prompt(name: str, key: str, **kwargs) -> str:
    """
    便捷函数：获取格式化后的 prompt。
    
    Args:
        name: 配置文件名（如 "screening", "interview"）
        key: prompt 键名
        **kwargs: 模板变量
        
    Returns:
        格式化后的 prompt 字符串
        
    Example:
        >>> prompt = get_prompt("screening", "hr_system", hr_rules="...")
    """
    return get_prompt_loader().get(name, key, **kwargs)


def get_config(name: str, key: str | None = None) -> Any:
    """
    便捷函数：获取配置值。
    
    Args:
        name: 配置文件名
        key: 配置键名
        
    Returns:
        配置值
        
    Example:
        >>> scales = get_config("analysis", "rubric_scales")
    """
    return get_prompt_loader().get_config(name, key)
