# -*- coding: utf-8 -*-
"""
Agent 经验管理器模块

核心功能：
1. learn() - 从 HR 反馈中学习：提炼规则 -> 向量化 -> 存储
2. recall() - 语义检索：查找与当前上下文相关的历史经验
"""
from typing import List, Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embedding import get_embedding_client, cosine_similarity
from app.core.reranker import get_reranker_client
from app.crud import experience_crud
from app.models import AgentExperience, AgentExperienceCreate

from .llm_client import get_llm_client
from .prompts import get_prompt, get_config


class ExperienceManager:
    """
    Agent 经验管理器
    
    负责经验的学习（存储）和回忆（检索）。
    """
    
    def __init__(self):
        self._llm = get_llm_client()
        self._embedding = get_embedding_client()
        self._reranker = get_reranker_client()
    
    async def learn(
        self,
        db: AsyncSession,
        category: str,
        feedback: str,
        context: str,
    ) -> AgentExperience:
        """
        从 HR 反馈中学习经验
        
        流程：
        1. 调用 LLM 将反馈提炼为通用规则
        2. 对规则生成 Embedding 向量
        3. 存入数据库
        
        Args:
            db: 数据库会话
            category: 经验类别 (screening/interview/analysis)
            feedback: HR 原始反馈
            context: 触发反馈的上下文摘要
            
        Returns:
            创建的经验对象
        """
        # 1. 提炼规则
        learned_rule = await self._extract_rule(feedback, context)
        logger.info("提炼经验规则: {} -> {}", feedback[:50], learned_rule[:50])
        
        # 2. 生成向量
        embedding = await self._get_embedding(learned_rule)
        
        # 3. 创建并存储经验
        experience_data = AgentExperienceCreate(
            category=category,
            source_feedback=feedback,
            learned_rule=learned_rule,
            context_summary=context[:500],  # 截断上下文
            embedding=embedding,
        )
        
        experience = await experience_crud.create(db, obj_in=experience_data)
        logger.info("经验已存储: id={}, category={}", experience.id, category)
        
        return experience
    
    async def recall(
        self,
        db: AsyncSession,
        category: str,
        context: str,
        top_k: int = 5,
        threshold: float = 0.2,
    ) -> List[AgentExperience]:
        """
        两阶段语义检索相关经验（Embedding粗召回 + Reranker精排）
        
        流程：
        1. 对当前上下文生成 Embedding
        2. 在同类别经验中按余弦相似度粗召回 top_k*2 条
        3. 使用 Reranker 对候选经验精排
        4. 过滤低于阈值的经验，返回 Top-K
        
        Args:
            db: 数据库会话
            category: 经验类别
            context: 当前上下文
            top_k: 返回数量
            threshold: Reranker 相关性阈值（默认 0.2）
            
        Returns:
            相关经验列表（按相关性降序，仅包含高于阈值的经验）
        """
        # 获取该类别的所有经验
        all_experiences = await experience_crud.get_all_by_category(db, category)
        
        if not all_experiences:
            logger.debug("类别 {} 暂无经验记录", category)
            return []
        
        # 生成当前上下文的向量
        context_embedding = await self._get_embedding(context)
        
        # 如果无法生成向量，返回空列表
        if not context_embedding:
            logger.warning("无法生成上下文向量，跳过经验检索")
            return []
        
        # === 阶段1: Embedding 粗召回 ===
        scored_experiences = []
        for exp in all_experiences:
            if exp.embedding:
                similarity = cosine_similarity(context_embedding, exp.embedding)
                scored_experiences.append((similarity, exp))
        
        # 按相似度降序排序，取 top_k*2 作为候选
        scored_experiences.sort(key=lambda x: x[0], reverse=True)
        candidates = scored_experiences[:top_k * 2]
        
        if not candidates:
            logger.debug("类别 {} 无有效候选经验", category)
            return []
        
        # === 阶段2: Reranker 精排 ===
        if self._reranker.is_configured() and len(candidates) > 1:
            try:
                # 构建文档列表用于重排序
                documents = [
                    f"{exp.context_summary}\n{exp.learned_rule}" 
                    for _, exp in candidates
                ]
                
                rerank_results = await self._reranker.rerank(
                    query=context,
                    documents=documents,
                    top_n=top_k
                )
                
                # 根据 Reranker 结果过滤并排序
                results = []
                for r in rerank_results:
                    if r.get("relevance_score", 0) >= threshold:
                        idx = r.get("index", 0)
                        if idx < len(candidates):
                            results.append(candidates[idx][1])
                            logger.debug(
                                "经验 {} Reranker 分数 {:.3f} 通过阈值 {:.2f}",
                                candidates[idx][1].id, r["relevance_score"], threshold
                            )
                    else:
                        logger.debug(
                            "经验 Reranker 分数 {:.3f} 低于阈值 {:.2f}，已过滤",
                            r.get("relevance_score", 0), threshold
                        )
                
                logger.debug(
                    "检索到 {} 条相关经验 (category={}, reranker=True)",
                    len(results), category
                )
                return results
                
            except Exception as e:
                logger.warning("Reranker 调用失败，降级为 Embedding 结果: {}", e)
        
        # === 降级: 仅使用 Embedding 结果 ===
        # 使用较高阈值 0.7 过滤（Embedding 相似度范围不同）
        embedding_threshold = 0.7
        results = [
            exp for sim, exp in candidates[:top_k] 
            if sim >= embedding_threshold
        ]
        
        logger.debug(
            "检索到 {} 条相关经验 (category={}, reranker=False)",
            len(results), category
        )
        return results
    
    def format_experiences_for_prompt(
        self,
        experiences: List[AgentExperience],
    ) -> str:
        """
        将经验列表格式化为可插入 Prompt 的文本
        
        Args:
            experiences: 经验列表
            
        Returns:
            格式化后的文本
        """
        if not experiences:
            return get_config("experience", "no_experience") or ""
        
        prefix = get_config("experience", "inject_prefix") or ""
        item_template = get_config("experience", "experience_item") or "{index}. {rule}"
        
        items = []
        for i, exp in enumerate(experiences, 1):
            item = item_template.format(index=i, rule=exp.learned_rule)
            items.append(item)
        
        return f"{prefix}\n" + "\n".join(items)
    
    async def _extract_rule(self, feedback: str, context: str) -> str:
        """调用 LLM 提炼规则"""
        system_prompt = get_config("experience", "extract_rule.system")
        user_prompt = get_prompt(
            "experience", "extract_rule.user",
            feedback=feedback,
            context=context[:1000],  # 截断上下文
        )
        
        try:
            result = await self._llm.complete(
                system_prompt, 
                user_prompt, 
                temperature=0.3
            )
            return result.strip()
        except Exception as exc:
            logger.error("提炼规则失败: {}", exc)
            # 降级：直接使用原始反馈
            return f"根据反馈：{feedback}"
    
    async def _get_embedding(self, text: str) -> List[float]:
        """获取文本的 Embedding 向量"""
        if not self._embedding.is_configured():
            logger.warning("Embedding 未配置，返回空向量")
            return []
        
        try:
            return await self._embedding.embed(text)
        except Exception as exc:
            logger.error("获取 Embedding 失败: {}", exc)
            return []


# 单例
_experience_manager: Optional[ExperienceManager] = None


def get_experience_manager() -> ExperienceManager:
    """获取 ExperienceManager 单例"""
    global _experience_manager
    if _experience_manager is None:
        _experience_manager = ExperienceManager()
    return _experience_manager
