"""
简历筛选任务模型模块
"""
from typing import TYPE_CHECKING, Optional
from enum import Enum
from sqlalchemy import String, Text, Float, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .application import Application


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"        # 等待中
    RUNNING = "running"        # 运行中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败


class ScreeningTask(BaseModel):
    """
    简历筛选任务模型
    
    存储 AI 简历筛选的过程和结果
    """
    __tablename__ = "screening_tasks"
    __table_args__ = (
        UniqueConstraint('application_id', name='uq_screening_task_application'),
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
    
    # ========== 任务状态 ==========
    status: Mapped[str] = mapped_column(
        String(20),
        default=TaskStatus.PENDING.value,
        index=True,
        comment="任务状态"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息"
    )
    
    # ========== 筛选结果 ==========
    score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="综合评分(0-100)"
    )
    dimension_scores: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="各维度评分详情"
    )
    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="筛选总结"
    )
    recommendation: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="推荐结果: strong/moderate/weak"
    )
    
    # ========== 报告存储 ==========
    report_content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="报告内容(Markdown)"
    )
    
    # ========== 关联关系 ==========
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="screening_task"
    )
    
    def __repr__(self) -> str:
        return f"<ScreeningTask(id={self.id}, status={self.status})>"
