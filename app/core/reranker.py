# -*- coding: utf-8 -*-
"""
Reranker 客户端模块

调用 Reranker API 对候选文档进行精排，提升 RAG 检索质量。
"""
from typing import List, Dict, Optional
from threading import Lock

import httpx
from loguru import logger

from app.core.config import settings


class RerankerClient:
    """
    Reranker 客户端单例类。
    
    使用 SiliconFlow API 调用 BAAI/bge-reranker-v2-m3 等模型。
    """

    _instance: Optional["RerankerClient"] = None
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

        self.model = settings.reranker_model
        self.api_key = settings.reranker_api_key
        self.base_url = settings.reranker_base_url
        
        self._initialized = True
        if self.is_configured():
            logger.info(
                "RerankerClient initialized: model={}, base_url={}",
                self.model,
                self.base_url,
            )
        else:
            logger.warning("RerankerClient not configured, reranker features disabled")

    def is_configured(self) -> bool:
        """检查 Reranker 是否已正确配置。"""
        return bool(self.model and self.api_key and self.base_url)

    async def rerank(
        self, 
        query: str, 
        documents: List[str], 
        top_n: int = 5
    ) -> List[Dict]:
        """
        对候选文档进行重排序。
        
        Args:
            query: 查询文本
            documents: 候选文档列表
            top_n: 返回前 N 个结果
            
        Returns:
            排序后的结果列表，每项包含:
            - index: 原始文档索引
            - relevance_score: 相关性分数
            - document: 文档内容（如果 return_documents=True）
            
        Raises:
            ValueError: 如果 Reranker 未配置
            httpx.HTTPError: 如果 API 调用失败
        """
        if not self.is_configured():
            raise ValueError("Reranker API 未配置，请检查 .env 文件中的 RERANKER_* 配置")
        
        if not documents:
            return []
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "top_n": min(top_n, len(documents)),
            "return_documents": True,
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
                return data.get("results", [])
                
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "Reranker API 调用失败: status={}, response={}",
                    exc.response.status_code,
                    exc.response.text[:500],
                )
                raise
            except Exception as exc:
                logger.error("Reranker API 调用异常: {}", exc)
                raise

    def get_status(self) -> dict:
        """获取 Reranker 客户端状态。"""
        return {
            "configured": self.is_configured(),
            "model": self.model,
            "base_url": self.base_url,
        }


def get_reranker_client() -> RerankerClient:
    """获取 RerankerClient 单例实例。"""
    return RerankerClient()
