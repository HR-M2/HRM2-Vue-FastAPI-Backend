"""
简历筛选任务模型模块 - SQLModel 版本
"""
from typing import Optional, List, TYPE_CHECKING
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship, Column, JSON, UniqueConstraint
from sqlalchemy import Column as SAColumn, String, ForeignKey

from .base import SQLModelBase, TimestampMixin, IDMixin, TimestampResponse

if TYPE_CHECKING:
    from .application import Application


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ==================== 嵌套 Schema ====================

class ScreeningScore(SQLModelBase):
    """筛选评分详情"""
    comprehensive_score: Optional[float] = Field(None, ge=0, le=100, description="综合评分")
    hr_score: Optional[int] = Field(None, description="HR评分")
    technical_score: Optional[int] = Field(None, description="技术评分")
    manager_score: Optional[int] = Field(None, description="管理评分")


# ==================== 表模型 ====================

class ScreeningTask(TimestampMixin, IDMixin, SQLModel, table=True):
    """简历筛选任务表模型"""
    __tablename__ = "screening_tasks"
    __table_args__ = (
        UniqueConstraint('application_id', name='uq_screening_task_application'),
    )
    
    # 外键
    application_id: str = Field(
        sa_column=SAColumn(String, ForeignKey("applications.id", ondelete="CASCADE"), unique=True, index=True, nullable=False),
        description="应聘申请ID"
    )
    
    # 任务状态
    status: str = Field(TaskStatus.PENDING.value, index=True, description="任务状态")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    # 筛选结果
    score: Optional[float] = Field(None, ge=0, le=100, description="综合评分")
    dimension_scores: Optional[dict] = Field(default=None, sa_column=Column(JSON), description="各维度评分")
    summary: Optional[str] = Field(None, description="筛选总结")
    recommendation: Optional[str] = Field(None, max_length=20, description="推荐结果")
    report_content: Optional[str] = Field(None, description="报告内容(Markdown)")
    
    # RAG 经验引用记录（用于追溯 AI 决策依据）
    applied_experience_ids: Optional[list] = Field(
        default=None,
        sa_column=Column(JSON),
        description="本次筛选引用的经验 ID 列表"
    )
    
    # 关联关系
    application: Optional["Application"] = Relationship(back_populates="screening_task")
    
    def __repr__(self) -> str:
        return f"<ScreeningTask(id={self.id}, status={self.status})>"


# ==================== 请求 Schema ====================

class ScreeningTaskCreate(SQLModelBase):
    """创建筛选任务请求"""
    application_id: str = Field(..., description="应聘申请ID")


class ScreeningResultUpdate(SQLModelBase):
    """更新筛选结果请求"""
    status: Optional[str] = Field(None, description="任务状态")
    score: Optional[float] = Field(None, ge=0, le=100, description="综合评分")
    dimension_scores: Optional[ScreeningScore] = Field(None, description="各维度评分")
    summary: Optional[str] = Field(None, description="筛选总结")
    recommendation: Optional[str] = Field(None, description="推荐结果")
    report_content: Optional[str] = Field(None, description="报告内容")
    error_message: Optional[str] = Field(None, description="错误信息")
    applied_experience_ids: Optional[List[str]] = Field(None, description="引用的经验 ID 列表")


# ==================== 响应 Schema ====================

class ScreeningTaskResponse(TimestampResponse):
    """筛选任务响应"""
    application_id: str
    status: str
    score: Optional[float]
    dimension_scores: Optional[ScreeningScore] = None
    summary: Optional[str]
    recommendation: Optional[str]
    report_content: Optional[str]
    error_message: Optional[str]
    applied_experience_ids: Optional[List[str]] = None
    
    # 关联信息
    candidate_name: Optional[str] = None
    position_title: Optional[str] = None
    resume_content: Optional[str] = None
    
    # 引用的经验详情（可选，由 API 填充）
    applied_experiences: Optional[List[dict]] = None
