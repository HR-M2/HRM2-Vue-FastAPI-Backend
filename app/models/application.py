"""
应聘申请模型模块 - SQLModel 版本

Application 是整个系统的核心表，连接岗位和简历
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, ForeignKey

from .base import SQLModelBase, TimestampMixin, IDMixin, TimestampResponse

if TYPE_CHECKING:
    from .position import Position, PositionListResponse
    from .resume import Resume, ResumeListResponse
    from .screening import ScreeningTask
    from .video import VideoAnalysis
    from .interview import InterviewSession
    from .analysis import ComprehensiveAnalysis


# ==================== 表模型 ====================

class Application(TimestampMixin, IDMixin, SQLModel, table=True):
    """
    应聘申请表模型（核心表）
    
    关联关系:
    - N:1 -> Position
    - N:1 -> Resume
    - 1:1 -> ScreeningTask
    - 1:1 -> VideoAnalysis
    - 1:1 -> InterviewSession
    - 1:1 -> ComprehensiveAnalysis
    """
    __tablename__ = "applications"
    
    # 外键
    position_id: str = Field(
        sa_column=Column(String, ForeignKey("positions.id", ondelete="CASCADE"), index=True, nullable=False),
        description="岗位ID"
    )
    resume_id: str = Field(
        sa_column=Column(String, ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False),
        description="简历ID"
    )
    
    # 备注
    notes: Optional[str] = Field(None, description="备注信息")
    
    # 软删除
    is_deleted: bool = Field(False, index=True, description="是否已删除")
    
    # 关联关系
    position: Optional["Position"] = Relationship(back_populates="applications")
    resume: Optional["Resume"] = Relationship(back_populates="applications")
    
    screening_task: Optional["ScreeningTask"] = Relationship(
        back_populates="application",
        sa_relationship_kwargs={"uselist": False, "lazy": "selectin", "cascade": "all, delete-orphan"}
    )
    video_analysis: Optional["VideoAnalysis"] = Relationship(
        back_populates="application",
        sa_relationship_kwargs={"uselist": False, "lazy": "selectin", "cascade": "all, delete-orphan"}
    )
    interview_session: Optional["InterviewSession"] = Relationship(
        back_populates="application",
        sa_relationship_kwargs={"uselist": False, "lazy": "selectin", "cascade": "all, delete-orphan"}
    )
    comprehensive_analysis: Optional["ComprehensiveAnalysis"] = Relationship(
        back_populates="application",
        sa_relationship_kwargs={"uselist": False, "lazy": "selectin", "cascade": "all, delete-orphan"}
    )
    
    def __repr__(self) -> str:
        return f"<Application(id={self.id})>"


# ==================== 请求 Schema ====================

class ApplicationCreate(SQLModelBase):
    """创建应聘申请请求"""
    position_id: str = Field(..., description="岗位ID")
    resume_id: str = Field(..., description="简历ID")
    notes: Optional[str] = Field(None, description="备注")


class ApplicationUpdate(SQLModelBase):
    """更新应聘申请请求"""
    notes: Optional[str] = None


# ==================== 响应 Schema ====================

class ApplicationResponse(TimestampResponse):
    """应聘申请响应"""
    position_id: str
    resume_id: str
    notes: Optional[str]
    
    # 关联信息（简化）
    position_title: Optional[str] = None
    candidate_name: Optional[str] = None


class ApplicationListResponse(TimestampResponse):
    """应聘申请列表项响应"""
    position_id: str
    resume_id: str
    position_title: Optional[str] = None
    candidate_name: Optional[str] = None
    # 与原版保持一致，使用完整的 Brief 对象
    screening_task: Optional["ScreeningTaskBrief"] = None


# ==================== Brief Schema (用于嵌套) ====================

class ScreeningTaskBrief(SQLModelBase):
    """筛选任务简要信息"""
    id: str
    status: str
    score: Optional[float]
    recommendation: Optional[str]
    created_at: datetime


class VideoAnalysisBrief(SQLModelBase):
    """视频分析简要信息"""
    id: str
    video_name: str
    status: str
    final_score: Optional[float] = None
    created_at: datetime


class InterviewSessionBrief(SQLModelBase):
    """面试会话简要信息"""
    id: str
    interview_type: str
    is_completed: bool
    final_score: Optional[float]
    message_count: int = 0
    has_report: bool = False
    created_at: datetime


class ComprehensiveAnalysisBrief(SQLModelBase):
    """综合分析简要信息"""
    id: str
    final_score: float
    recommendation_level: str
    created_at: datetime


# ==================== 详情响应 ====================

class ApplicationDetailResponse(ApplicationResponse):
    """应聘申请详情响应（包含关联数据）"""
    # 完整的关联对象（用于详情页）
    position: Optional["PositionListResponse"] = None
    resume: Optional["ResumeListResponse"] = None
    # Brief 类型（用于嵌套展示）
    screening_task: Optional[ScreeningTaskBrief] = None
    video_analysis: Optional[VideoAnalysisBrief] = None
    interview_session: Optional[InterviewSessionBrief] = None
    comprehensive_analysis: Optional[ComprehensiveAnalysisBrief] = None


# 解决循环导入：延迟导入类型
from .position import PositionListResponse
from .resume import ResumeListResponse

ApplicationDetailResponse.model_rebuild()
