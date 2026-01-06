# -*- coding: utf-8 -*-
"""
Embedding 客户端模块

调用 Embedding API 将文本转换为向量，用于语义检索。
"""
import asyncio
from typing import List, Optional
from threading import Lock

import httpx
from loguru import logger

from app.core.config import settings


class EmbeddingClient:
    """
    Embedding 客户端单例类。
    
    使用 SiliconFlow API (兼容 OpenAI 格式) 调用 BAAI/bge-m3 等模型。
    """

    _instance: Optional["EmbeddingClient"] = None
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

        self.model = settings.embedding_model
        self.api_key = settings.embedding_api_key
        self.base_url = settings.embedding_base_url
        
        self._initialized = True
        if self.is_configured():
            logger.info(
                "EmbeddingClient initialized: model={}, base_url={}",
                self.model,
                self.base_url,
            )
        else:
            logger.warning("EmbeddingClient not configured, embedding features disabled")

    def is_configured(self) -> bool:
        """检查 Embedding 是否已正确配置。"""
        return bool(self.model and self.api_key and self.base_url)

    async def embed(self, text: str) -> List[float]:
        """
        将单个文本转换为向量。
        
        Args:
            text: 需要嵌入的文本
            
        Returns:
            向量列表 (List[float])
            
        Raises:
            ValueError: 如果 Embedding 未配置
            httpx.HTTPError: 如果 API 调用失败
        """
        if not self.is_configured():
            raise ValueError("Embedding API 未配置，请检查 .env 文件中的 EMBEDDING_* 配置")
        
        result = await self.embed_batch([text])
        return result[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量将文本转换为向量。
        
        Args:
            texts: 需要嵌入的文本列表
            
        Returns:
            向量列表 (List[List[float]])
            
        Raises:
            ValueError: 如果 Embedding 未配置
            httpx.HTTPError: 如果 API 调用失败
        """
        if not self.is_configured():
            raise ValueError("Embedding API 未配置，请检查 .env 文件中的 EMBEDDING_* 配置")
        
        if not texts:
            return []
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "input": texts,
            "encoding_format": "float",
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                
                data = response.json()
                
                # OpenAI 格式: {"data": [{"embedding": [...], "index": 0}, ...]}
                embeddings = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
                return [item.get("embedding", []) for item in embeddings]
                
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "Embedding API 调用失败: status={}, response={}",
                    exc.response.status_code,
                    exc.response.text[:500],
                )
                raise
            except Exception as exc:
                logger.error("Embedding API 调用异常: {}", exc)
                raise

    def get_status(self) -> dict:
        """获取 Embedding 客户端状态。"""
        return {
            "configured": self.is_configured(),
            "model": self.model,
            "base_url": self.base_url,
        }


def get_embedding_client() -> EmbeddingClient:
    """获取 EmbeddingClient 单例实例。"""
    return EmbeddingClient()


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    计算两个向量的余弦相似度。
    
    Args:
        vec1: 向量1
        vec2: 向量2
        
    Returns:
        余弦相似度 (-1 到 1 之间)
    """
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(b * b for b in vec2) ** 0.5
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)
