"""
应聘申请模型模块

Application 是整个系统的核心表，连接岗位和简历，
并作为所有分析任务的关联主体
"""
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Text, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .position import Position
    from .resume import Resume
    from .screening import ScreeningTask
    from .video import VideoAnalysis
    from .interview import InterviewSession
    from .analysis import ComprehensiveAnalysis


class Application(BaseModel):
    """
    应聘申请模型（核心表）
    
    关联关系:
    - N:1 -> Position (一个岗位有多个申请)
    - N:1 -> Resume (一份简历可投多个岗位)
    - 1:1 -> ScreeningTask (筛选任务)
    - 1:1 -> VideoAnalysis (视频分析)
    - 1:1 -> InterviewSession (面试会话)
    - 1:1 -> ComprehensiveAnalysis (综合分析)
    """
    __tablename__ = "applications"
    
    # ========== 外键关联 ==========
    position_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("positions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="岗位ID"
    )
    resume_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="简历ID"
    )
    
    # ========== 备注 ==========
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="备注信息"
    )
    
    # ========== 软删除标记 ==========
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="是否已删除（软删除）"
    )
    
    # ========== 关联关系 ==========
    position: Mapped["Position"] = relationship(
        "Position",
        back_populates="applications"
    )
    resume: Mapped["Resume"] = relationship(
        "Resume",
        back_populates="applications"
    )
    screening_task: Mapped[Optional["ScreeningTask"]] = relationship(
        "ScreeningTask",
        back_populates="application",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    video_analysis: Mapped[Optional["VideoAnalysis"]] = relationship(
        "VideoAnalysis",
        back_populates="application",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    interview_session: Mapped[Optional["InterviewSession"]] = relationship(
        "InterviewSession",
        back_populates="application",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    comprehensive_analysis: Mapped[Optional["ComprehensiveAnalysis"]] = relationship(
        "ComprehensiveAnalysis",
        back_populates="application",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Application(id={self.id})>"
