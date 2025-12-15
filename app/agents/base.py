"""
Agent 基类模块

定义所有 Agent 的通用接口和方法
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from loguru import logger

from .llm_config import llm_config, LLMConfig


class BaseAgent(ABC):
    """
    Agent 基类
    
    所有业务 Agent 继承此类，实现具体的 AI 功能
    """
    
    # Agent 名称，子类需要覆盖
    name: str = "BaseAgent"
    
    # Agent 描述
    description: str = "基础 Agent"
    
    # 系统提示词
    system_prompt: str = "你是一个有帮助的 AI 助手。"
    
    def __init__(self, llm: Optional[LLMConfig] = None):
        """
        初始化 Agent
        
        Args:
            llm: LLM 配置实例，默认使用全局配置
        """
        self.llm = llm or llm_config
        self._conversation_history: List[Dict[str, str]] = []
    
    def _build_messages(
        self,
        user_message: str,
        *,
        system_prompt: Optional[str] = None,
        include_history: bool = False,
    ) -> List[Dict[str, str]]:
        """
        构建消息列表
        
        Args:
            user_message: 用户消息
            system_prompt: 系统提示词，默认使用类属性
            include_history: 是否包含历史对话
            
        Returns:
            消息列表
        """
        messages = [
            {"role": "system", "content": system_prompt or self.system_prompt}
        ]
        
        if include_history:
            messages.extend(self._conversation_history)
        
        messages.append({"role": "user", "content": user_message})
        return messages
    
    def add_to_history(self, role: str, content: str) -> None:
        """添加消息到历史记录"""
        self._conversation_history.append({"role": role, "content": content})
    
    def clear_history(self) -> None:
        """清空历史记录"""
        self._conversation_history.clear()
    
    async def chat(
        self,
        message: str,
        *,
        temperature: Optional[float] = None,
        include_history: bool = False,
    ) -> str:
        """
        与 Agent 对话
        
        Args:
            message: 用户消息
            temperature: 温度参数
            include_history: 是否包含历史对话
            
        Returns:
            Agent 回复
        """
        messages = self._build_messages(message, include_history=include_history)
        
        logger.info(f"[{self.name}] 处理请求...")
        response = await self.llm.chat(messages, temperature=temperature)
        
        if include_history:
            self.add_to_history("user", message)
            self.add_to_history("assistant", response)
        
        return response
    
    async def chat_json(
        self,
        message: str,
        *,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        与 Agent 对话，返回 JSON
        
        Args:
            message: 用户消息
            temperature: 温度参数
            
        Returns:
            解析后的 JSON 字典
        """
        messages = self._build_messages(message)
        
        logger.info(f"[{self.name}] 处理 JSON 请求...")
        return await self.llm.chat_json(messages, temperature=temperature)
    
    @abstractmethod
    async def run(self, *args, **kwargs) -> Any:
        """
        执行 Agent 主要任务
        
        子类必须实现此方法
        """
        pass
