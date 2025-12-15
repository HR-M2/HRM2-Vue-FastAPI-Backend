"""
面试会话相关 Schema
"""
from typing import Optional, List, Dict
from pydantic import Field

from .base import BaseSchema, TimestampSchema


class QARecord(BaseSchema):
    """问答记录"""
    
    round: int = Field(..., description="轮次")
    question: str = Field(..., description="问题")
    answer: str = Field(..., description="回答")
    score: Optional[float] = Field(None, description="评分")
    evaluation: Optional[str] = Field(None, description="评价")


class InterviewSessionCreate(BaseSchema):
    """创建面试会话请求"""
    
    application_id: str = Field(..., description="应聘申请ID")
    interview_type: str = Field("general", description="面试类型")
    config: Optional[Dict] = Field(default_factory=dict, description="面试配置")


class QARecordCreate(BaseSchema):
    """添加问答记录请求"""
    
    question: str = Field(..., min_length=1, description="问题")
    answer: str = Field(..., min_length=1, description="回答")
    score: Optional[float] = Field(None, ge=0, le=100, description="评分")
    evaluation: Optional[str] = Field(None, description="评价")


class GenerateQuestionsRequest(BaseSchema):
    """生成问题请求"""
    
    count: int = Field(5, ge=1, le=20, description="生成问题数量")
    difficulty: str = Field("medium", description="难度: easy/medium/hard")
    focus_areas: Optional[List[str]] = Field(None, description="关注领域")


class InterviewSessionUpdate(BaseSchema):
    """更新面试会话请求"""
    
    interview_type: Optional[str] = None
    config: Optional[Dict] = None
    question_pool: Optional[List[str]] = None
    is_completed: Optional[bool] = None
    final_score: Optional[float] = Field(None, ge=0, le=100)
    report: Optional[Dict] = None
    report_markdown: Optional[str] = None


class InterviewSessionResponse(TimestampSchema):
    """面试会话响应"""
    
    application_id: str
    interview_type: str
    config: Dict
    qa_records: List[QARecord]
    question_pool: List[str]
    is_completed: bool
    final_score: Optional[float]
    report: Optional[Dict]
    report_markdown: Optional[str]
    current_round: int = 0
    
    # 关联信息
    candidate_name: Optional[str] = None
    position_title: Optional[str] = None
