"""
统一的 LLM 客户端封装模块。

提供带并发控制和速率限制的 LLM 调用接口。
所有 LLM 调用都应通过此模块进行。
"""
import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI
from threading import Lock

from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """简单的速率限制器（令牌桶算法）"""
    
    def __init__(self, rate: int):
        """
        参数:
            rate: 每分钟允许的请求数
        """
        self.rate = rate
        self.tokens = rate
        self.last_update = time.time()
        self._lock = Lock()
    
    def acquire(self) -> bool:
        """尝试获取一个令牌，返回是否成功"""
        with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.rate, self.tokens + elapsed * (self.rate / 60.0))
            self.last_update = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False
    
    def wait_and_acquire(self):
        """等待直到可以获取令牌"""
        while not self.acquire():
            time.sleep(0.1)


class ConcurrencyLimiter:
    def __init__(self, max_concurrency: int):
        self._semaphore = asyncio.Semaphore(max_concurrency)
    
    async def acquire(self):
        await self._semaphore.acquire()
    
    def release(self):
        self._semaphore.release()


class LLMClient:
    """
    统一的 LLM 客户端。
    
    提供:
    - 并发控制
    - 速率限制
    - 统一的错误处理
    - JSON 响应解析
    """
    
    _instance: Optional['LLMClient'] = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.model = settings.llm_model
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url
        self.temperature = settings.llm_temperature
        self.timeout = settings.llm_timeout
        
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )
        
        self._rate_limiter = RateLimiter(settings.llm_rate_limit)
        self._concurrency_limiter = ConcurrencyLimiter(settings.llm_max_concurrency)
        
        self._initialized = True
        logger.info(
            f"LLMClient initialized: model={self.model}, "
            f"max_concurrency={settings.llm_max_concurrency}, "
            f"rate_limit={settings.llm_rate_limit}/min"
        )
    
    def _parse_json(self, content: str) -> Dict[str, Any]:
        """解析 JSON 响应，处理 markdown 代码块"""
        text = content.strip()
        
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}\n原始内容: {text[:500]}")
            raise ValueError(f"LLM 返回的结果不是有效的 JSON 格式: {str(e)}")
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        model: Optional[str] = None
    ) -> str:
        """
        异步发送聊天请求并返回文本响应。
        
        不会阻塞事件循环，适用于 FastAPI 异步端点。
        """
        # 异步等待速率限制
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._rate_limiter.wait_and_acquire)
        
        await self._concurrency_limiter.acquire()
        
        try:
            response = await self._client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature
            )
            
            if not response or not response.choices:
                raise ValueError("LLM 返回空响应")
            
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("LLM 返回内容为空")
            
            return content.strip()
            
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise
        finally:
            self._concurrency_limiter.release()
    
    async def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        异步发送聊天请求并返回解析后的 JSON。
        """
        content = await self.chat(messages, temperature, model)
        return self._parse_json(content)
    
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        model: Optional[str] = None
    ) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        return await self.chat(messages, temperature, model)
    
    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        异步便捷方法：发送 system + user 消息并返回解析后的 JSON。
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        return await self.chat_json(messages, temperature, model)
    
    def get_autogen_config(self) -> Dict[str, Any]:
        """
        获取 autogen 框架所需的配置格式。
        
        返回:
            autogen 配置字典
        """
        return {
            "config_list": [{
                "model": self.model,
                "api_key": self.api_key,
                "base_url": self.base_url,
                "temperature": self.temperature,
            }],
            "seed": 42,
            "timeout": self.timeout,
            "temperature": self.temperature,
        }
    
    def is_configured(self) -> bool:
        """检查 LLM 是否已正确配置"""
        return bool(self.api_key) and self.api_key != 'your-api-key-here'
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前 LLM 配置状态"""
        return {
            "model": self.model,
            "base_url": self.base_url,
            "api_key_configured": self.is_configured(),
            "temperature": self.temperature,
            "timeout": self.timeout,
            "max_concurrency": settings.llm_max_concurrency,
            "rate_limit": settings.llm_rate_limit,
        }


def get_llm_client() -> LLMClient:
    """获取 LLMClient 单例实例"""
    return LLMClient()


class TaskConcurrencyLimiter:
    """
    任务级别的并发限制器。
    
    用于限制同时运行的后台任务数量（如简历筛选任务）。
    这些任务使用 autogen 框架，绕过了 LLMClient 的并发控制。
    """
    
    _instance: Optional['TaskConcurrencyLimiter'] = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._max_tasks = settings.llm_max_concurrency
        self._current_tasks = 0
        self._task_lock = Lock()
        self._initialized = True
        logger.info(f"TaskConcurrencyLimiter initialized: max_tasks={self._max_tasks}")
    
    def acquire(self) -> bool:
        """尝试获取任务槽位，返回是否成功"""
        with self._task_lock:
            if self._current_tasks < self._max_tasks:
                self._current_tasks += 1
                logger.debug(f"Task slot acquired: {self._current_tasks}/{self._max_tasks}")
                return True
            return False
    
    def wait_and_acquire(self, timeout: float = 300.0) -> bool:
        """
        等待并获取任务槽位。
        
        参数:
            timeout: 最大等待时间（秒），默认 5 分钟
            
        返回:
            是否成功获取
        """
        start_time = time.time()
        while True:
            if self.acquire():
                return True
            if time.time() - start_time > timeout:
                logger.warning(f"Task slot acquisition timeout after {timeout}s")
                return False
            time.sleep(0.5)
    
    def release(self):
        """释放任务槽位"""
        with self._task_lock:
            if self._current_tasks > 0:
                self._current_tasks -= 1
                logger.debug(f"Task slot released: {self._current_tasks}/{self._max_tasks}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        with self._task_lock:
            return {
                "max_tasks": self._max_tasks,
                "current_tasks": self._current_tasks,
                "available_slots": self._max_tasks - self._current_tasks
            }


def get_task_limiter() -> TaskConcurrencyLimiter:
    """获取任务并发限制器单例"""
    return TaskConcurrencyLimiter()
