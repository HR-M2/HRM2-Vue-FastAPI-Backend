"""
视频分析模型模块 - SQLModel 版本
"""
from typing import Optional, Dict, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, JSON, UniqueConstraint
from sqlalchemy import Column as SAColumn, String, ForeignKey

from .base import SQLModelBase, TimestampMixin, IDMixin, TimestampResponse
from .screening import TaskStatus

if TYPE_CHECKING:
    from .application import Application


# ==================== 嵌套 Schema ====================

class BigFiveScores(SQLModelBase):
    """大五人格评分"""
    openness: Optional[float] = Field(None, ge=0, le=100, description="开放性")
    conscientiousness: Optional[float] = Field(None, ge=0, le=100, description="尽责性")
    extraversion: Optional[float] = Field(None, ge=0, le=100, description="外向性")
    agreeableness: Optional[float] = Field(None, ge=0, le=100, description="宜人性")
    neuroticism: Optional[float] = Field(None, ge=0, le=100, description="神经质")


# ==================== 表模型 ====================

class VideoAnalysis(TimestampMixin, IDMixin, SQLModel, table=True):
    """视频分析表模型"""
    __tablename__ = "video_analyses"
    __table_args__ = (
        UniqueConstraint('application_id', name='uq_video_analysis_application'),
    )
    
    # 外键
    application_id: str = Field(
        sa_column=SAColumn(String, ForeignKey("applications.id", ondelete="CASCADE"), unique=True, index=True, nullable=False),
        description="应聘申请ID"
    )
    
    # 视频信息
    video_name: str = Field(..., max_length=255, description="视频名称")
    video_path: Optional[str] = Field(None, max_length=500, description="视频存储路径")
    file_size: int = Field(0, ge=0, description="文件大小(字节)")
    duration: int = Field(0, ge=0, description="视频时长(秒)")
    
    # 任务状态
    status: str = Field(TaskStatus.PENDING.value, index=True, description="分析状态")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    # 大五人格评分
    openness: Optional[float] = Field(None, ge=0, le=100, description="开放性")
    conscientiousness: Optional[float] = Field(None, ge=0, le=100, description="尽责性")
    extraversion: Optional[float] = Field(None, ge=0, le=100, description="外向性")
    agreeableness: Optional[float] = Field(None, ge=0, le=100, description="宜人性")
    neuroticism: Optional[float] = Field(None, ge=0, le=100, description="神经质")
    
    # 其他分析结果
    confidence_score: Optional[float] = Field(None, description="置信度评分")
    fraud_score: Optional[float] = Field(None, description="欺诈风险评分")
    summary: Optional[str] = Field(None, description="分析摘要")
    raw_result: Optional[dict] = Field(default=None, sa_column=Column(JSON), description="原始分析结果")
    
    # 关联关系
    application: Optional["Application"] = Relationship(back_populates="video_analysis")
    
    @property
    def big_five_scores(self) -> BigFiveScores:
        """大五人格评分汇总"""
        return BigFiveScores(
            openness=self.openness,
            conscientiousness=self.conscientiousness,
            extraversion=self.extraversion,
            agreeableness=self.agreeableness,
            neuroticism=self.neuroticism,
        )
    
    def __repr__(self) -> str:
        return f"<VideoAnalysis(id={self.id}, video={self.video_name})>"


# ==================== 请求 Schema ====================

class VideoAnalysisCreate(SQLModelBase):
    """创建视频分析请求"""
    application_id: str = Field(..., description="应聘申请ID")
    video_name: str = Field(..., max_length=255, description="视频名称")
    video_path: Optional[str] = Field(None, description="视频存储路径")
    file_size: int = Field(0, ge=0, description="文件大小")
    duration: int = Field(0, ge=0, description="视频时长(秒)")


class VideoResultUpdate(SQLModelBase):
    """更新视频分析结果请求"""
    status: Optional[str] = Field(None, description="分析状态")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    # 大五人格评分
    openness: Optional[float] = Field(None, ge=0, le=100)
    conscientiousness: Optional[float] = Field(None, ge=0, le=100)
    extraversion: Optional[float] = Field(None, ge=0, le=100)
    agreeableness: Optional[float] = Field(None, ge=0, le=100)
    neuroticism: Optional[float] = Field(None, ge=0, le=100)
    
    # 其他分析结果
    confidence_score: Optional[float] = None
    fraud_score: Optional[float] = None
    summary: Optional[str] = None
    raw_result: Optional[Dict] = None


# ==================== 响应 Schema ====================

class VideoAnalysisResponse(TimestampResponse):
    """视频分析响应"""
    application_id: str
    video_name: str
    video_path: Optional[str]
    file_size: int
    duration: int
    status: str
    error_message: Optional[str]
    
    # 大五人格
    big_five_scores: Optional[BigFiveScores] = None
    
    # 其他结果
    confidence_score: Optional[float]
    fraud_score: Optional[float]
    summary: Optional[str]
    
    # 关联信息
    candidate_name: Optional[str] = None
    position_title: Optional[str] = None
