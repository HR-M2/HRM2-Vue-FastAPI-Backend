"""
面试会话模型模块
"""
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Text, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .application import Application


class InterviewSession(BaseModel):
    """
    面试会话模型
    
    存储 AI 辅助面试的问答消息和报告
    
    messages JSON 格式示例:
    [
        {
            "seq": 1,
            "role": "interviewer",
            "content": "请介绍一下你自己",
            "timestamp": "2024-01-01T10:00:00"
        },
        {
            "seq": 2,
            "role": "candidate",
            "content": "我是...",
            "timestamp": "2024-01-01T10:01:00"
        },
        ...
    ]
    """
    __tablename__ = "interview_sessions"
    __table_args__ = (
        UniqueConstraint('application_id', name='uq_interview_session_application'),
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
    
    # ========== 面试配置 ==========
    interview_type: Mapped[str] = mapped_column(
        String(50),
        default="general",
        comment="面试类型: general/technical/behavioral"
    )
    config: Mapped[Optional[dict]] = mapped_column(
        JSON,
        default=dict,
        comment="面试配置(问题数量、难度等)"
    )
    
    # ========== 问答消息 ==========
    messages: Mapped[Optional[list]] = mapped_column(
        JSON,
        default=list,
        comment="问答消息列表"
    )
    
    # ========== 问题池 ==========
    question_pool: Mapped[Optional[list]] = mapped_column(
        JSON,
        default=list,
        comment="AI生成的问题池"
    )
    
    # ========== 面试报告 ==========
    is_completed: Mapped[bool] = mapped_column(
        default=False,
        comment="是否已完成"
    )
    final_score: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="最终评分"
    )
    report: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="面试报告(JSON)"
    )
    report_markdown: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="面试报告(Markdown)"
    )
    
    # ========== 关联关系 ==========
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="interview_session"
    )
    
    @property
    def message_count(self) -> int:
        """消息数量"""
        return len(self.messages) if self.messages else 0
    
    @property
    def has_report(self) -> bool:
        if not self.report_markdown:
            return False
        placeholder_markers = ["待 AI 服务生成", "面试报告占位"]
        return not any(marker in self.report_markdown for marker in placeholder_markers)
    
    def __repr__(self) -> str:
        return f"<InterviewSession(id={self.id}, messages={self.message_count})>"
