"""
简历筛选相关 Schema
"""
from typing import Optional
from pydantic import Field

from .base import BaseSchema, TimestampSchema


class ScreeningDimensionScores(BaseSchema):
    """
    筛选任务维度评分
    
    基于 ai_services.py 中 _parse_screening_result 的实际输出结构
    """
    hr_score: Optional[int] = Field(None, description="HR评分")
    technical_score: Optional[int] = Field(None, description="技术评分")
    manager_score: Optional[int] = Field(None, description="管理评分")


class ScreeningTaskCreate(BaseSchema):
    """创建筛选任务请求"""
    
    application_id: str = Field(..., description="应聘申请ID")


class ScreeningResultUpdate(BaseSchema):
    """更新筛选结果请求"""
    
    status: Optional[str] = Field(None, description="任务状态")
    score: Optional[float] = Field(None, ge=0, le=100, description="综合评分")
    dimension_scores: Optional[ScreeningDimensionScores] = Field(None, description="各维度评分")
    summary: Optional[str] = Field(None, description="筛选总结")
    recommendation: Optional[str] = Field(None, description="推荐结果")
    report_content: Optional[str] = Field(None, description="报告内容")
    error_message: Optional[str] = Field(None, description="错误信息")


class ScreeningTaskResponse(TimestampSchema):
    """筛选任务响应"""
    
    application_id: str
    status: str
    score: Optional[float]
    dimension_scores: Optional[ScreeningDimensionScores] = Field(None, description="各维度评分")
    summary: Optional[str]
    recommendation: Optional[str]
    report_content: Optional[str]
    error_message: Optional[str]
    
    # 关联信息
    candidate_name: Optional[str] = None
    position_title: Optional[str] = None
    resume_content: Optional[str] = None
