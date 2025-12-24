"""
统一的 LLM 客户端封装。
"""
import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI
from threading import Lock
from loguru import logger

from app.core.config import settings


class RateLimiter:
    """简单的速率限制器（令牌桶算法）。"""

    def __init__(self, rate: int):
        self.rate = rate
        self.tokens = rate
        self.last_update = time.time()
        self._lock = Lock()

    def acquire(self) -> bool:
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
        while not self.acquire():
            time.sleep(0.1)


class ConcurrencyLimiter:
    """并发限制器。"""

    def __init__(self, max_concurrency: int):
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def acquire(self):
        await self._semaphore.acquire()

    def release(self):
        self._semaphore.release()


class LLMClient:
    """
    统一的 LLM 客户端，提供并发控制、速率限制和 JSON 解析。
    """

    _instance: Optional["LLMClient"] = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self.model = settings.llm_model
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url
        self.temperature = settings.llm_temperature
        self.timeout = settings.llm_timeout

        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

        self._rate_limiter = RateLimiter(settings.llm_rate_limit)
        self._concurrency_limiter = ConcurrencyLimiter(settings.llm_max_concurrency)

        self._initialized = True
        logger.info(
            "LLMClient initialized: model={}, max_concurrency={}, rate_limit={}/min",
            self.model,
            settings.llm_max_concurrency,
            settings.llm_rate_limit,
        )

    def _parse_json(self, content: str) -> Dict[str, Any]:
        """解析 JSON 响应，兼容 markdown 代码块。"""
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
        except json.JSONDecodeError as exc:
            logger.error("JSON 解析失败: {}\n原始内容: {}", exc, text[:500])
            raise ValueError(f"LLM 返回的结果不是有效的 JSON 格式: {exc}")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        model: Optional[str] = None,
    ) -> str:
        """异步发送聊天请求并返回文本响应。"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._rate_limiter.wait_and_acquire)

        await self._concurrency_limiter.acquire()
        try:
            response = await self._client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
            )
            if not response or not response.choices:
                raise ValueError("LLM 返回空响应")
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("LLM 返回内容为空")
            return content.strip()
        except Exception as exc:
            logger.error("LLM 调用失败: {}", exc)
            raise
        finally:
            self._concurrency_limiter.release()

    async def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """异步发送聊天请求并返回解析后的 JSON。"""
        content = await self.chat(messages, temperature, model)
        return self._parse_json(content)

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
    ) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return await self.chat(messages, temperature, model)

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """异步便捷方法：发送 system + user 消息并返回解析后的 JSON。"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return await self.chat_json(messages, temperature, model)

    def get_autogen_config(self) -> Dict[str, Any]:
        """获取 autogen 框架所需的配置格式。"""
        return {
            "config_list": [
                {
                    "model": self.model,
                    "api_key": self.api_key,
                    "base_url": self.base_url,
                    "temperature": self.temperature,
                }
            ],
            "seed": 42,
            "timeout": self.timeout,
            "temperature": self.temperature,
        }

    def is_configured(self) -> bool:
        """检查 LLM 是否已正确配置。"""
        return bool(self.api_key) and self.api_key != "your-api-key-here"

    def get_status(self) -> Dict[str, Any]:
        """获取当前 LLM 配置状态。"""
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
    """获取 LLMClient 单例实例。"""
    return LLMClient()


def get_embedding_config() -> Dict[str, Any]:
    """获取 Embedding 模型配置。"""
    return {
        "model": getattr(settings, "embedding_model", ""),
        "api_key": getattr(settings, "embedding_api_key", settings.llm_api_key),
        "base_url": getattr(settings, "embedding_base_url", settings.llm_base_url),
    }


class TaskConcurrencyLimiter:
    """任务级别的并发限制器，用于限制后台任务数量。"""

    _instance: Optional["TaskConcurrencyLimiter"] = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._max_tasks = settings.llm_max_concurrency
        self._current_tasks = 0
        self._task_lock = Lock()
        self._initialized = True
        logger.info("TaskConcurrencyLimiter initialized: max_tasks={}", self._max_tasks)

    def acquire(self) -> bool:
        """尝试获取任务槽位。"""
        with self._task_lock:
            if self._current_tasks < self._max_tasks:
                self._current_tasks += 1
                logger.debug(
                    "Task slot acquired: {}/{}", self._current_tasks, self._max_tasks
                )
                return True
            return False

    def wait_and_acquire(self, timeout: float = 300.0) -> bool:
        """
        等待并获取任务槽位。
        参数:
            timeout: 最大等待时间（秒）
        """
        start_time = time.time()
        while True:
            if self.acquire():
                return True
            if time.time() - start_time > timeout:
                logger.warning("Task slot acquisition timeout after {}s", timeout)
                return False
            time.sleep(0.5)

    def release(self):
        """释放任务槽位。"""
        with self._task_lock:
            if self._current_tasks > 0:
                self._current_tasks -= 1
                logger.debug(
                    "Task slot released: {}/{}", self._current_tasks, self._max_tasks
                )

    def get_status(self) -> Dict[str, Any]:
        """获取当前任务并发状态。"""
        with self._task_lock:
            return {
                "max_tasks": self._max_tasks,
                "current_tasks": self._current_tasks,
                "available_slots": self._max_tasks - self._current_tasks,
            }


def get_task_limiter() -> TaskConcurrencyLimiter:
    """获取任务并发限制器单例。"""
    return TaskConcurrencyLimiter()
