"""
面试会话模型模块 - SQLModel 版本
"""
from typing import Optional, List, Dict, Literal, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship, Column, JSON, UniqueConstraint
from sqlalchemy import Column as SAColumn, String, ForeignKey

from .base import SQLModelBase, TimestampMixin, IDMixin, TimestampResponse

if TYPE_CHECKING:
    from .application import Application


# ==================== 嵌套 Schema ====================

class QAMessage(SQLModelBase):
    """问答消息"""
    seq: int = Field(..., description="消息序号")
    role: Literal["interviewer", "candidate"] = Field(..., description="角色")
    content: str = Field(..., description="内容")
    timestamp: datetime = Field(..., description="时间戳")


class QAMessageCreate(SQLModelBase):
    """创建问答消息"""
    role: Literal["interviewer", "candidate"] = Field(..., description="角色")
    content: str = Field(..., min_length=1, description="内容")


class MessagesSyncRequest(SQLModelBase):
    """同步消息请求"""
    messages: List[QAMessageCreate] = Field(..., description="完整对话记录")


class GenerateQuestionsRequest(SQLModelBase):
    """生成问题请求"""
    count: int = Field(5, ge=1, le=20, description="生成问题数量")
    difficulty: str = Field("medium", description="难度: easy/medium/hard")
    focus_areas: Optional[List[str]] = Field(None, description="关注领域")


class AppliedExperienceItem(SQLModelBase):
    """引用的经验详情（用于 API 响应）"""
    id: str = Field(..., description="经验 ID")
    learned_rule: str = Field(..., description="AI 提炼的规则")
    source_feedback: str = Field(..., description="HR 原始反馈")
    category: str = Field(..., description="经验类别")


# ==================== 表模型 ====================

class InterviewSession(TimestampMixin, IDMixin, SQLModel, table=True):
    """面试会话表模型"""
    __tablename__ = "interview_sessions"
    __table_args__ = (
        UniqueConstraint('application_id', name='uq_interview_session_application'),
    )
    
    # 外键
    application_id: str = Field(
        sa_column=SAColumn(String, ForeignKey("applications.id", ondelete="CASCADE"), unique=True, index=True, nullable=False),
        description="应聘申请ID"
    )
    
    # 面试配置
    interview_type: str = Field("general", max_length=50, description="面试类型")
    config: Optional[dict] = Field(default_factory=dict, sa_column=Column(JSON), description="面试配置")
    
    # 问答消息
    messages: Optional[list] = Field(default_factory=list, sa_column=Column(JSON), description="问答消息列表")
    question_pool: Optional[list] = Field(default_factory=list, sa_column=Column(JSON), description="问题池")
    
    # 面试报告
    is_completed: bool = Field(False, description="是否已完成")
    final_score: Optional[float] = Field(None, ge=0, le=100, description="最终评分")
    report: Optional[dict] = Field(default=None, sa_column=Column(JSON), description="面试报告(JSON) - DEPRECATED: 请使用 report_markdown 字段")
    report_markdown: Optional[str] = Field(None, description="面试报告(Markdown)")
    
    # RAG 经验引用记录（用于追溯 AI 决策依据）
    applied_experience_ids: Optional[list] = Field(
        default=None,
        sa_column=Column(JSON),
        description="本次面试报告引用的经验 ID 列表"
    )
    
    # 关联关系
    application: Optional["Application"] = Relationship(back_populates="interview_session")
    
    @property
    def message_count(self) -> int:
        """消息数量"""
        return len(self.messages) if self.messages else 0
    
    @property
    def has_report(self) -> bool:
        """是否有有效报告"""
        if not self.report_markdown:
            return False
        placeholder_markers = ["待 AI 服务生成", "面试报告占位"]
        return not any(marker in self.report_markdown for marker in placeholder_markers)
    
    def __repr__(self) -> str:
        return f"<InterviewSession(id={self.id}, messages={self.message_count})>"


# ==================== 请求 Schema ====================

class InterviewSessionCreate(SQLModelBase):
    """创建面试会话请求"""
    application_id: str = Field(..., description="应聘申请ID")
    interview_type: str = Field("general", description="面试类型")
    config: Optional[Dict] = Field(default_factory=dict, description="面试配置")


class InterviewSessionUpdate(SQLModelBase):
    """更新面试会话请求"""
    interview_type: Optional[str] = None
    config: Optional[Dict] = None
    question_pool: Optional[List[str]] = None
    is_completed: Optional[bool] = None
    final_score: Optional[float] = Field(None, ge=0, le=100)
    report: Optional[Dict] = None
    report_markdown: Optional[str] = None
    applied_experience_ids: Optional[List[str]] = None


# ==================== 响应 Schema ====================

class InterviewSessionResponse(TimestampResponse):
    """面试会话响应"""
    application_id: str
    interview_type: str
    config: Dict
    messages: List[QAMessage]
    question_pool: List[str]
    is_completed: bool
    final_score: Optional[float]
    report: Optional[Dict]
    report_markdown: Optional[str]
    applied_experience_ids: Optional[List[str]] = None
    message_count: int = 0
    has_report: bool = False
    
    # 关联信息
    candidate_name: Optional[str] = None
    position_title: Optional[str] = None
    
    # 引用的经验详情（由 API 填充）
    applied_experiences: Optional[List[AppliedExperienceItem]] = None
