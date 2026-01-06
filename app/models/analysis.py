"""
综合分析模型模块 - SQLModel 版本
"""
from typing import Optional, Dict, List, TYPE_CHECKING
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship, Column, JSON, UniqueConstraint
from sqlalchemy import Column as SAColumn, String, ForeignKey

from .base import SQLModelBase, TimestampMixin, IDMixin, TimestampResponse
from .experience import AppliedExperienceItem

if TYPE_CHECKING:
    from .application import Application


class RecommendationLevel(str, Enum):
    """推荐等级枚举"""
    STRONGLY_RECOMMENDED = "strongly_recommended"
    RECOMMENDED = "recommended"
    CONDITIONAL = "conditional"
    NOT_RECOMMENDED = "not_recommended"


# ==================== 嵌套 Schema ====================

class DimensionScoreItem(SQLModelBase):
    """单个维度评分项"""
    dimension_score: Optional[int] = Field(None, ge=1, le=5, description="维度评分(1-5)")
    dimension_name: Optional[str] = Field(None, description="维度名称")
    weight: Optional[float] = Field(None, description="权重")
    sub_scores: Optional[Dict[str, int]] = Field(None, description="子维度评分")
    strengths: Optional[List[str]] = Field(None, description="优势列表")
    weaknesses: Optional[List[str]] = Field(None, description="不足列表")
    analysis: Optional[str] = Field(None, description="详细分析说明")


# ==================== 表模型 ====================

class ComprehensiveAnalysis(TimestampMixin, IDMixin, SQLModel, table=True):
    """综合分析表模型"""
    __tablename__ = "comprehensive_analyses"
    __table_args__ = (
        UniqueConstraint('application_id', name='uq_comprehensive_analysis_application'),
    )
    
    # 外键
    application_id: str = Field(
        sa_column=SAColumn(String, ForeignKey("applications.id", ondelete="CASCADE"), unique=True, index=True, nullable=False),
        description="应聘申请ID"
    )
    
    # 综合评分
    final_score: float = Field(..., ge=0, le=100, description="综合得分")
    
    # 推荐结果
    recommendation_level: str = Field(
        RecommendationLevel.CONDITIONAL.value,
        max_length=30,
        description="推荐等级"
    )
    recommendation_reason: Optional[str] = Field(None, description="推荐理由")
    suggested_action: Optional[str] = Field(None, description="建议行动")
    
    # 各维度评分
    dimension_scores: Optional[dict] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="各维度评分详情"
    )
    
    # 分析报告
    report: Optional[str] = Field(None, description="综合分析报告(Markdown)")
    
    # 输入数据快照
    input_snapshot: Optional[dict] = Field(
        default_factory=dict,
        sa_column=Column(JSON),
        description="输入数据快照"
    )
    
    # RAG 经验引用记录（用于追溯 AI 决策依据）
    applied_experience_ids: Optional[list] = Field(
        default=None,
        sa_column=Column(JSON),
        description="本次综合分析引用的经验 ID 列表"
    )
    
    # 关联关系
    application: Optional["Application"] = Relationship(back_populates="comprehensive_analysis")
    
    def __repr__(self) -> str:
        return f"<ComprehensiveAnalysis(id={self.id}, score={self.final_score})>"


# ==================== 请求 Schema ====================

class ComprehensiveAnalysisCreate(SQLModelBase):
    """创建综合分析请求"""
    application_id: str = Field(..., description="应聘申请ID")


class ComprehensiveAnalysisUpdate(SQLModelBase):
    """更新综合分析请求"""
    final_score: Optional[float] = Field(None, ge=0, le=100, description="综合得分")
    recommendation_level: Optional[str] = Field(None, description="推荐等级")
    recommendation_reason: Optional[str] = Field(None, description="推荐理由")
    suggested_action: Optional[str] = Field(None, description="建议行动")
    dimension_scores: Optional[Dict] = Field(None, description="各维度评分")
    report: Optional[str] = Field(None, description="分析报告")
    input_snapshot: Optional[Dict] = Field(None, description="输入数据快照")
    applied_experience_ids: Optional[List[str]] = Field(None, description="引用的经验 ID 列表")


# ==================== 响应 Schema ====================

class ComprehensiveAnalysisResponse(TimestampResponse):
    """综合分析响应"""
    application_id: str
    final_score: float
    recommendation_level: str
    recommendation_reason: Optional[str]
    suggested_action: Optional[str]
    dimension_scores: Dict[str, DimensionScoreItem] = Field(default_factory=dict)
    report: Optional[str]
    input_snapshot: Dict
    applied_experience_ids: Optional[List[str]] = None
    
    # 关联信息
    candidate_name: Optional[str] = None
    position_title: Optional[str] = None
    
    # 引用的经验详情（由 API 填充）
    applied_experiences: Optional[List[AppliedExperienceItem]] = None
