"""
视频分析相关 Schema
"""
from typing import Optional, Dict
from pydantic import Field

from .base import BaseSchema, TimestampSchema


class VideoAnalysisCreate(BaseSchema):
    """创建视频分析请求"""
    
    application_id: str = Field(..., description="应聘申请ID")
    video_name: str = Field(..., max_length=255, description="视频名称")
    video_path: Optional[str] = Field(None, description="视频存储路径")
    file_size: int = Field(0, ge=0, description="文件大小")
    duration: int = Field(0, ge=0, description="视频时长(秒)")


class VideoResultUpdate(BaseSchema):
    """更新视频分析结果请求"""
    
    status: Optional[str] = Field(None, description="分析状态")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    # 大五人格评分
    openness: Optional[float] = Field(None, ge=0, le=100, description="开放性")
    conscientiousness: Optional[float] = Field(None, ge=0, le=100, description="尽责性")
    extraversion: Optional[float] = Field(None, ge=0, le=100, description="外向性")
    agreeableness: Optional[float] = Field(None, ge=0, le=100, description="宜人性")
    neuroticism: Optional[float] = Field(None, ge=0, le=100, description="神经质")
    
    # 其他分析结果
    confidence_score: Optional[float] = Field(None, description="置信度")
    fraud_score: Optional[float] = Field(None, description="欺诈风险")
    summary: Optional[str] = Field(None, description="分析摘要")
    raw_result: Optional[Dict] = Field(None, description="原始结果")


class BigFiveScores(BaseSchema):
    """大五人格评分"""
    
    openness: Optional[float] = Field(None, description="开放性")
    conscientiousness: Optional[float] = Field(None, description="尽责性")
    extraversion: Optional[float] = Field(None, description="外向性")
    agreeableness: Optional[float] = Field(None, description="宜人性")
    neuroticism: Optional[float] = Field(None, description="神经质")


class VideoAnalysisResponse(TimestampSchema):
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
