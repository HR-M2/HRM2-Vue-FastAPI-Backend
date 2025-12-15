"""
LLM 配置模块

统一管理 LLM 客户端配置和实例
"""
from typing import Optional, List, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from loguru import logger

from app.core.config import settings


class LLMConfig:
    """
    LLM 配置管理类
    
    支持 OpenAI 兼容 API（DeepSeek、OpenAI、Qwen、GLM 等）
    """
    
    def __init__(self):
        self._client: Optional[AsyncOpenAI] = None
    
    @property
    def client(self) -> AsyncOpenAI:
        """延迟初始化 OpenAI 客户端"""
        if self._client is None:
            if not settings.llm_api_key:
                raise ValueError("LLM_API_KEY 未配置，请在 .env 文件中设置")
            
            self._client = AsyncOpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                timeout=settings.llm_timeout,
            )
            logger.info(f"LLM 客户端初始化: {settings.llm_base_url}")
        return self._client
    
    @property
    def model(self) -> str:
        """当前使用的模型"""
        return settings.llm_model
    
    @property
    def temperature(self) -> float:
        """默认温度参数"""
        return settings.llm_temperature
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
        **kwargs
    ) -> str:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表 [{"role": "user/system/assistant", "content": "..."}]
            model: 模型名称，默认使用配置
            temperature: 温度参数，默认使用配置
            max_tokens: 最大输出 token 数
            response_format: 响应格式 {"type": "json_object"} 强制 JSON 输出
            
        Returns:
            模型回复文本
        """
        try:
            params = {
                "model": model or self.model,
                "messages": messages,
                "temperature": temperature if temperature is not None else self.temperature,
                "max_tokens": max_tokens,
                **kwargs
            }
            if response_format:
                params["response_format"] = response_format
            
            response = await self.client.chat.completions.create(**params)
            content = response.choices[0].message.content or ""
            
            logger.debug(f"LLM 调用成功, tokens: {response.usage.total_tokens if response.usage else 'N/A'}")
            return content
            
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise
    
    async def chat_json(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        发送聊天请求，强制返回 JSON
        
        Returns:
            解析后的 JSON 字典
        """
        import json
        
        content = await self.chat(
            messages,
            response_format={"type": "json_object"},
            **kwargs
        )
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}\n原始内容: {content[:500]}")
            raise ValueError(f"LLM 返回的内容不是有效 JSON: {e}")
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 4096,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天请求
        
        Yields:
            模型回复文本片段
        """
        try:
            stream = await self.client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"LLM 流式调用失败: {e}")
            raise


# 全局 LLM 配置实例
llm_config = LLMConfig()
