"""
视频分析模型模块
"""
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Text, Integer, Float, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel
from .screening import TaskStatus

if TYPE_CHECKING:
    from .application import Application


class VideoAnalysis(BaseModel):
    """
    视频分析模型
    
    存储面试视频分析的过程和结果（大五人格等）
    """
    __tablename__ = "video_analyses"
    __table_args__ = (
        UniqueConstraint('application_id', name='uq_video_analysis_application'),
    )
    
    # ========== 外键关联 ==========
    application_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="应聘申请ID"
    )
    
    # ========== 视频信息 ==========
    video_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="视频名称"
    )
    video_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="视频存储路径"
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="文件大小(字节)"
    )
    duration: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="视频时长(秒)"
    )
    
    # ========== 任务状态 ==========
    status: Mapped[str] = mapped_column(
        String(20),
        default=TaskStatus.PENDING.value,
        index=True,
        comment="分析状态"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息"
    )
    
    # ========== 大五人格评分 ==========
    openness: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="开放性(0-100)"
    )
    conscientiousness: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="尽责性(0-100)"
    )
    extraversion: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="外向性(0-100)"
    )
    agreeableness: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="宜人性(0-100)"
    )
    neuroticism: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="神经质(0-100)"
    )
    
    # ========== 其他分析结果 ==========
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="置信度评分"
    )
    fraud_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="欺诈风险评分"
    )
    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="分析摘要"
    )
    raw_result: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="原始分析结果"
    )
    
    # ========== 关联关系 ==========
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="video_analysis"
    )
    
    @property
    def big_five_scores(self) -> dict:
        """大五人格评分汇总"""
        return {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
        }
    
    def __repr__(self) -> str:
        return f"<VideoAnalysis(id={self.id}, video={self.video_name})>"
