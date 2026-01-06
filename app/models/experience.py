# -*- coding: utf-8 -*-
"""
Agent 经验模型模块 - SQLModel 版本

存储 HR 反馈提炼的评估经验，支持 RAG 检索。
"""
from typing import Optional, List
from enum import Enum
from sqlmodel import SQLModel, Field, Column, JSON

from .base import SQLModelBase, TimestampMixin, IDMixin, TimestampResponse


class ExperienceCategory(str, Enum):
    """经验类别枚举"""
    SCREENING = "screening"
    INTERVIEW = "interview"
    ANALYSIS = "analysis"


# ==================== 基础 Schema ====================

class AgentExperienceBase(SQLModelBase):
    """经验基础字段"""
    category: str = Field(..., max_length=20, description="经验类别: screening/interview/analysis")
    source_feedback: str = Field(..., description="HR 原始反馈")
    learned_rule: str = Field(..., description="AI 提炼的通用规则")
    context_summary: str = Field(..., description="触发经验的上下文摘要")


class AppliedExperienceItem(SQLModelBase):
    """引用的经验详情（用于 API 响应，展示报告引用了哪些历史经验）"""
    id: str = Field(..., description="经验 ID")
    learned_rule: str = Field(..., description="AI 提炼的规则")
    source_feedback: str = Field(..., description="HR 原始反馈")
    category: str = Field(..., description="经验类别")


# ==================== 表模型 ====================

class AgentExperience(AgentExperienceBase, TimestampMixin, IDMixin, SQLModel, table=True):
    """Agent 经验表模型"""
    __tablename__ = "agent_experiences"
    
    # 向量存储 (JSON 格式)
    embedding: Optional[list] = Field(
        default=None,
        sa_column=Column(JSON),
        description="文本向量 (List[float])"
    )
    
    def __repr__(self) -> str:
        return f"<AgentExperience(id={self.id}, category={self.category})>"


# ==================== 请求 Schema ====================

class AgentExperienceCreate(AgentExperienceBase):
    """创建经验请求"""
    embedding: Optional[List[float]] = Field(None, description="文本向量")


class FeedbackRequest(SQLModelBase):
    """HR 反馈请求"""
    category: str = Field(..., description="报告类别: screening/interview/analysis")
    target_id: str = Field(..., description="目标 ID (task_id/session_id/analysis_id)")
    feedback: str = Field(..., min_length=5, description="HR 反馈内容")


# ==================== 响应 Schema ====================

class AgentExperienceResponse(TimestampResponse):
    """经验响应"""
    category: str
    source_feedback: str
    learned_rule: str
    context_summary: str


class FeedbackResponse(SQLModelBase):
    """反馈处理响应"""
    learned_rule: str = Field(..., description="提炼的经验规则")
    new_report: Optional[str] = Field(None, description="重新生成的报告内容")
    experience_id: str = Field(..., description="存储的经验 ID")
