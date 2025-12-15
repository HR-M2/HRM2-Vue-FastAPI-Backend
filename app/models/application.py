"""
应聘申请模型模块

Application 是整个系统的核心表，连接岗位和简历，
并作为所有分析任务的关联主体
"""
from typing import TYPE_CHECKING, List, Optional
from enum import Enum
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .position import Position
    from .resume import Resume
    from .screening import ScreeningTask
    from .video import VideoAnalysis
    from .interview import InterviewSession
    from .analysis import ComprehensiveAnalysis


class ApplicationStatus(str, Enum):
    """应聘申请状态枚举"""
    PENDING = "pending"              # 待处理
    SCREENING = "screening"          # 简历筛选中
    SCREENED = "screened"            # 已初筛
    INTERVIEWING = "interviewing"    # 面试中
    INTERVIEWED = "interviewed"      # 已面试
    ANALYZING = "analyzing"          # 综合分析中
    OFFER = "offer"                  # 已发Offer
    REJECTED = "rejected"            # 已拒绝
    WITHDRAWN = "withdrawn"          # 已撤回


class Application(BaseModel):
    """
    应聘申请模型（核心表）
    
    关联关系:
    - N:1 -> Position (一个岗位有多个申请)
    - N:1 -> Resume (一份简历可投多个岗位)
    - 1:N -> ScreeningTask (筛选任务)
    - 1:N -> VideoAnalysis (视频分析)
    - 1:N -> InterviewSession (面试会话)
    - 1:N -> ComprehensiveAnalysis (综合分析)
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
    
    # ========== 状态管理 ==========
    status: Mapped[str] = mapped_column(
        String(20),
        default=ApplicationStatus.PENDING.value,
        index=True,
        comment="申请状态"
    )
    
    # ========== 备注 ==========
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="备注信息"
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
    screening_tasks: Mapped[List["ScreeningTask"]] = relationship(
        "ScreeningTask",
        back_populates="application",
        lazy="selectin"
    )
    video_analyses: Mapped[List["VideoAnalysis"]] = relationship(
        "VideoAnalysis",
        back_populates="application",
        lazy="selectin"
    )
    interview_sessions: Mapped[List["InterviewSession"]] = relationship(
        "InterviewSession",
        back_populates="application",
        lazy="selectin"
    )
    comprehensive_analyses: Mapped[List["ComprehensiveAnalysis"]] = relationship(
        "ComprehensiveAnalysis",
        back_populates="application",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<Application(id={self.id}, status={self.status})>"
