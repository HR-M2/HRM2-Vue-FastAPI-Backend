# -*- coding: utf-8 -*-
"""
岗位 AI 服务：根据岗位描述生成结构化岗位要求。
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional
from loguru import logger

from .llm_client import get_llm_client, get_embedding_config
from .prompts import get_prompt, get_config


class PositionService:
    """AI 生成岗位要求服务。"""

    def __init__(self):
        self._llm = get_llm_client()
        emb_cfg = get_embedding_config()
        self.embedding_api_key = emb_cfg.get("api_key", "")
        self.embedding_base_url = emb_cfg.get("base_url", "")
        self.embedding_model = emb_cfg.get("model", "")

    async def generate_position_requirements(
        self,
        description: str,
        documents: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """根据岗位描述生成岗位要求 JSON。"""
        context_parts: List[str] = []
        if documents:
            context_parts.append("以下是参考文档内容：")
            for doc in documents:
                name = doc.get("name", "未命名文档")
                content = doc.get("content", "")
                if content:
                    max_len = 3000
                    if len(content) > max_len:
                        content = content[:max_len] + "...(内容已截断)"
                    context_parts.append(f"\n--- {name} ---\n{content}")
        context = "\n".join(context_parts)

        # 加载 schema 用于构建系统提示
        position_schema = get_prompt("position", "position_schema")
        system_prompt = get_prompt("position", "system_prompt", position_schema=position_schema)
        user_prompt = get_prompt("position", "user_prompt", description=description, context=context)
        
        position_data = await self._llm.complete_json(system_prompt, user_prompt)
        self._normalize_position_data(position_data)
        return position_data

    def _normalize_position_data(self, data: Dict[str, Any]) -> None:
        """校验并修正生成的数据结构。"""
        if "title" not in data:
            raise ValueError("生成的数据缺少必要字段: title")

        array_fields = ["required_skills", "optional_skills", "education", "certifications"]
        for field in array_fields:
            if field in data and not isinstance(data[field], list):
                data[field] = [data[field]] if data[field] else []
            elif field not in data:
                data[field] = []

        if "salary_range" in data:
            sr = data["salary_range"]
            if isinstance(sr, list) and len(sr) >= 2:
                data["salary_range"] = [int(sr[0]), int(sr[1])]
            else:
                data["salary_range"] = [0, 0]
        else:
            data["salary_range"] = [0, 0]

        if "project_requirements" not in data or not isinstance(data["project_requirements"], dict):
            data["project_requirements"] = {"min_projects": 0, "team_lead_experience": False}
        else:
            pr = data["project_requirements"]
            if "min_projects" not in pr:
                pr["min_projects"] = 0
            if "team_lead_experience" not in pr:
                pr["team_lead_experience"] = False

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        获取文本向量表示（预留，便于未来语义搜索）。
        """
        if not self.embedding_model:
            logger.warning("Embedding model not configured")
            return []
        try:
            from openai import AsyncOpenAI
            embedding_client = AsyncOpenAI(
                api_key=self.embedding_api_key,
                base_url=self.embedding_base_url,
                timeout=30,
            )
            resp = await embedding_client.embeddings.create(model=self.embedding_model, input=texts)
            return [item.embedding for item in resp.data]
        except Exception as exc:
            logger.error("获取向量失败: {}", exc)
            return []


_position_service: PositionService | None = None


def get_position_service() -> PositionService:
    """获取 PositionService 单例。"""
    global _position_service
    if _position_service is None:
        _position_service = PositionService()
    return _position_service
