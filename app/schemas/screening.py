"""
简历筛选相关 Schema
"""
from typing import Optional, Dict
from pydantic import Field

from .base import BaseSchema, TimestampSchema


class ScreeningTaskCreate(BaseSchema):
    """创建筛选任务请求"""
    
    application_id: str = Field(..., description="应聘申请ID")


class ScreeningResultUpdate(BaseSchema):
    """更新筛选结果请求"""
    
    status: Optional[str] = Field(None, description="任务状态")
    progress: Optional[int] = Field(None, ge=0, le=100, description="进度")
    score: Optional[float] = Field(None, ge=0, le=100, description="综合评分")
    dimension_scores: Optional[Dict] = Field(None, description="各维度评分")
    summary: Optional[str] = Field(None, description="筛选总结")
    recommendation: Optional[str] = Field(None, description="推荐结果")
    report_content: Optional[str] = Field(None, description="报告内容")
    error_message: Optional[str] = Field(None, description="错误信息")


class ScreeningTaskResponse(TimestampSchema):
    """筛选任务响应"""
    
    application_id: str
    status: str
    progress: int
    score: Optional[float]
    dimension_scores: Optional[Dict]
    summary: Optional[str]
    recommendation: Optional[str]
    report_content: Optional[str]
    error_message: Optional[str]
    
    # 关联信息
    candidate_name: Optional[str] = None
    position_title: Optional[str] = None
    resume_content: Optional[str] = None
