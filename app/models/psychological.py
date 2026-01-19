"""
心理分析报告模型模块
"""
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Text, ForeignKey, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .immersive import ImmersiveSession
    from .application import Application


class PsychologicalReport(BaseModel):
    """
    心理分析报告模型
    
    与沉浸式面试会话(ImmersiveSession)1:1关联
    在"最终推荐"界面点击"生成报告"时创建
    
    数据来源:
    - 面试记录中的大五人格评分
    - 面试记录中的欺骗检测评分
    - 面试记录中的抑郁风险评分
    - 面试发言模式分析
    """
    __tablename__ = "psychological_reports"
    
    # ========== 外键关联 ==========
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("immersive_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="沉浸式面试会话ID"
    )
    application_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="应聘申请ID"
    )
    
    # ========== 大五人格分析 ==========
    big_five_scores: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="大五人格各维度得分"
    )
    big_five_analysis: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="大五人格详细分析"
    )
    
    # ========== 欺骗检测分析 ==========
    deception_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="整体欺骗分数(0-1)"
    )
    deception_analysis: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="欺骗检测详细分析"
    )
    
    # ========== 抑郁风险分析 ==========
    depression_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="整体抑郁分数(0-100)"
    )
    depression_level: Mapped[str] = mapped_column(
        String(20),
        default="unknown",
        comment="抑郁风险等级: low/medium/high"
    )
    depression_analysis: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="抑郁风险详细分析"
    )
    
    # ========== 发言模式分析 ==========
    speech_pattern_analysis: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="发言模式分析(语速、占比、风格等)"
    )
    
    # ========== 综合评估 ==========
    overall_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="心理健康综合评分(0-100)"
    )
    risk_level: Mapped[str] = mapped_column(
        String(20),
        default="unknown",
        comment="综合风险等级: low/medium/high"
    )
    overall_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="综合评估摘要"
    )
    recommendations: Mapped[Optional[list]] = mapped_column(
        JSON,
        default=list,
        comment="建议列表"
    )
    
    # ========== 完整报告 ==========
    report_markdown: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Markdown格式完整报告"
    )
    
    # ========== 输入快照 ==========
    input_snapshot: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="生成报告时的输入数据快照"
    )
    
    # ========== 关联关系 ==========
    session: Mapped["ImmersiveSession"] = relationship(
        "ImmersiveSession",
        back_populates="psychological_report"
    )
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="psychological_reports"
    )
    
    def __repr__(self) -> str:
        return f"<PsychologicalReport(id={self.id}, session_id={self.session_id}, risk_level={self.risk_level})>"
