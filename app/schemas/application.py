"""
应聘申请相关 Schema
"""
from typing import Optional, List
from datetime import datetime
from pydantic import Field

from .base import BaseSchema, TimestampSchema
from .position import PositionListResponse
from .resume import ResumeListResponse


class ApplicationBase(BaseSchema):
    """应聘申请基础字段"""
    
    position_id: str = Field(..., description="岗位ID")
    resume_id: str = Field(..., description="简历ID")
    notes: Optional[str] = Field(None, description="备注")


class ApplicationCreate(ApplicationBase):
    """创建应聘申请请求"""
    pass


class ApplicationUpdate(BaseSchema):
    """更新应聘申请请求"""
    
    notes: Optional[str] = None


class ApplicationResponse(TimestampSchema):
    """应聘申请响应"""
    
    position_id: str
    resume_id: str
    notes: Optional[str]
    
    # 关联信息（简化）
    position_title: Optional[str] = None
    candidate_name: Optional[str] = None


class ApplicationListResponse(TimestampSchema):
    """应聘申请列表项响应"""
    
    position_id: str
    resume_id: str
    position_title: Optional[str] = None
    candidate_name: Optional[str] = None


class ScreeningTaskBrief(BaseSchema):
    """筛选任务简要信息"""
    
    id: str
    status: str
    score: Optional[float]
    recommendation: Optional[str]
    created_at: datetime


class VideoAnalysisBrief(BaseSchema):
    """视频分析简要信息"""
    
    id: str
    video_name: str
    status: str
    final_score: Optional[float] = None
    created_at: datetime


class InterviewSessionBrief(BaseSchema):
    """面试会话简要信息"""
    
    id: str
    interview_type: str
    is_completed: bool
    final_score: Optional[float]
    current_round: int = 0
    created_at: datetime


class ComprehensiveAnalysisBrief(BaseSchema):
    """综合分析简要信息"""
    
    id: str
    final_score: float
    recommendation_level: str
    created_at: datetime


class ApplicationDetailResponse(ApplicationResponse):
    """应聘申请详情响应（包含关联数据）"""
    
    position: Optional[PositionListResponse] = None
    resume: Optional[ResumeListResponse] = None
    screening_tasks: List[ScreeningTaskBrief] = []
    video_analyses: List[VideoAnalysisBrief] = []
    interview_sessions: List[InterviewSessionBrief] = []
    comprehensive_analyses: List[ComprehensiveAnalysisBrief] = []
