"""
岗位 AI 服务：根据岗位描述生成结构化岗位要求。
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional
from loguru import logger

from .llm_client import get_llm_client, get_embedding_config

# ================= 提示词模板 =================

POSITION_SCHEMA = """
{
    "position": "岗位名称（字符串）",
    "description": "岗位描述（字符串）",
    "required_skills": ["必备技能列表"],
    "optional_skills": ["可选技能列表"],
    "min_experience": 最低工作经验年数（整数）,
    "education": ["学历要求，可选值：大专、本科、硕士、博士"],
    "certifications": ["证书要求列表"],
    "salary_range": [最低月薪, 最高月薪],
    "project_requirements": {
        "min_projects": 最少项目数量（整数）,
        "team_lead_experience": 是否要求团队管理经验（布尔值）
    }
}
"""

SYSTEM_PROMPT_POSITION = f"""你是一位专业的人力资源专家，擅长根据岗位描述生成结构化的招聘要求。

你需要根据用户提供的岗位描述（可能是简短的一句话，也可能是详细的需求说明），生成完整的岗位要求JSON。

输出格式必须严格遵循以下JSON结构：
{POSITION_SCHEMA}

注意事项：
1. 根据岗位类型合理推断所需技能、学历、经验等要求
2. 技能列表应该具体且与岗位相关
3. 薪资范围应该符合市场行情（单位：元/月）
4. 如果信息不足，使用合理的默认值
5. 只输出JSON，不要有任何其他文字说明
6. 确保JSON格式正确，可以被解析"""

USER_PROMPT_POSITION = """请根据以下岗位描述生成招聘要求：

{description}
{context}

请直接输出JSON格式的岗位要求，不要包含任何其他内容。"""


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

        user_prompt = USER_PROMPT_POSITION.format(description=description, context=context)
        position_data = await self._llm.complete_json(SYSTEM_PROMPT_POSITION, user_prompt)
        self._normalize_position_data(position_data)
        return position_data

    def _normalize_position_data(self, data: Dict[str, Any]) -> None:
        """校验并修正生成的数据结构。"""
        if "position" not in data:
            raise ValueError("生成的数据缺少必要字段: position")

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
