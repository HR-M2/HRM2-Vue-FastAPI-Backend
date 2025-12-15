"""
综合分析模型模块
"""
from typing import TYPE_CHECKING, Optional
from enum import Enum
from sqlalchemy import String, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .application import Application


class RecommendationLevel(str, Enum):
    """推荐等级枚举"""
    STRONGLY_RECOMMENDED = "strongly_recommended"  # 强烈推荐
    RECOMMENDED = "recommended"                    # 推荐
    CONDITIONAL = "conditional"                    # 有条件推荐
    NOT_RECOMMENDED = "not_recommended"            # 不推荐


class ComprehensiveAnalysis(BaseModel):
    """
    综合分析模型
    
    整合简历筛选、视频分析、面试记录等数据，
    基于 Rubric 量表进行多维度评估
    """
    __tablename__ = "comprehensive_analyses"
    
    # ========== 外键关联 ==========
    application_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="应聘申请ID"
    )
    
    # ========== 综合评分 ==========
    final_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="综合得分(0-100)"
    )
    
    # ========== 推荐结果 ==========
    recommendation_level: Mapped[str] = mapped_column(
        String(30),
        default=RecommendationLevel.CONDITIONAL.value,
        comment="推荐等级"
    )
    recommendation_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="推荐理由"
    )
    suggested_action: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="建议行动"
    )
    
    # ========== 各维度评分 ==========
    dimension_scores: Mapped[Optional[dict]] = mapped_column(
        JSON,
        default=dict,
        comment="各维度评分详情"
    )
    
    # ========== 分析报告 ==========
    report: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="综合分析报告(Markdown)"
    )
    
    # ========== 输入数据快照 ==========
    input_snapshot: Mapped[Optional[dict]] = mapped_column(
        JSON,
        default=dict,
        comment="输入数据快照(便于追溯)"
    )
    
    # ========== 关联关系 ==========
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="comprehensive_analyses"
    )
    
    def __repr__(self) -> str:
        return f"<ComprehensiveAnalysis(id={self.id}, score={self.final_score})>"
