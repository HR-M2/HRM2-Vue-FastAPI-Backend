"""
心理分析报告 Schema 模块
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import Field

from .base import BaseSchema, TimestampSchema


# ========== 子结构 Schema ==========

class BigFiveScores(BaseSchema):
    """大五人格得分"""
    openness: float = Field(0.5, ge=0, le=1, description="开放性")
    conscientiousness: float = Field(0.5, ge=0, le=1, description="尽责性")
    extraversion: float = Field(0.5, ge=0, le=1, description="外向性")
    agreeableness: float = Field(0.5, ge=0, le=1, description="宜人性")
    neuroticism: float = Field(0.5, ge=0, le=1, description="神经质")


class BigFiveAnalysis(BaseSchema):
    """大五人格分析"""
    scores: BigFiveScores = Field(..., description="各维度得分")
    personality_type: str = Field("", description="人格类型概括")
    strengths: List[str] = Field(default_factory=list, description="优势特质")
    potential_concerns: List[str] = Field(default_factory=list, description="潜在关注点")
    work_style: str = Field("", description="工作风格建议")
    team_fit: str = Field("", description="团队适配建议")


class DeceptionAnalysis(BaseSchema):
    """欺骗检测分析"""
    overall_score: float = Field(0.0, ge=0, le=1, description="整体欺骗分数(0-1,越低越可信)")
    credibility_level: str = Field("unknown", description="可信度等级: high/medium/low")
    suspicious_responses: List[Dict[str, Any]] = Field(default_factory=list, description="可疑回答列表")
    analysis_summary: str = Field("", description="分析总结")


class DepressionAnalysis(BaseSchema):
    """抑郁风险分析"""
    average_score: float = Field(0.0, ge=0, le=100, description="平均抑郁分数(0-100)")
    risk_level: str = Field("unknown", description="风险等级: low/medium/high")
    trend: str = Field("stable", description="趋势: stable/increasing/decreasing")
    high_risk_moments: List[Dict[str, Any]] = Field(default_factory=list, description="高风险时刻列表")
    interpretation: str = Field("", description="解读说明")


class SpeechPatternAnalysis(BaseSchema):
    """发言模式分析"""
    speaking_ratio: float = Field(0.0, ge=0, le=1, description="候选人发言占比")
    total_chars: int = Field(0, ge=0, description="候选人总字数")
    avg_response_length: float = Field(0.0, ge=0, description="平均回答长度(字)")
    response_count: int = Field(0, ge=0, description="回答次数")
    communication_style: str = Field("", description="沟通风格")
    fluency_assessment: str = Field("", description="流畅度评估")
    confidence_level: str = Field("", description="自信程度")


# ========== 请求 Schema ==========

class PsychologicalReportGenerate(BaseSchema):
    """生成心理分析报告请求"""
    session_id: str = Field(..., description="沉浸式面试会话ID")


# ========== 响应 Schema ==========

class PsychologicalReportResponse(TimestampSchema):
    """心理分析报告响应"""
    session_id: str = Field(..., description="沉浸式面试会话ID")
    application_id: str = Field(..., description="应聘申请ID")
    
    # 大五人格分析
    big_five_scores: Optional[Dict[str, float]] = Field(None, description="大五人格得分")
    big_five_analysis: Optional[BigFiveAnalysis] = Field(None, description="大五人格详细分析")
    
    # 欺骗检测分析
    deception_score: float = Field(0.0, description="整体欺骗分数")
    deception_analysis: Optional[DeceptionAnalysis] = Field(None, description="欺骗检测详细分析")
    
    # 抑郁风险分析
    depression_score: float = Field(0.0, description="整体抑郁分数")
    depression_level: str = Field("unknown", description="抑郁风险等级")
    depression_analysis: Optional[DepressionAnalysis] = Field(None, description="抑郁风险详细分析")
    
    # 发言模式分析
    speech_pattern_analysis: Optional[SpeechPatternAnalysis] = Field(None, description="发言模式分析")
    
    # 综合评估
    overall_score: float = Field(0.0, description="心理健康综合评分")
    risk_level: str = Field("unknown", description="综合风险等级")
    overall_summary: Optional[str] = Field(None, description="综合评估摘要")
    recommendations: List[str] = Field(default_factory=list, description="建议列表")
    
    # 完整报告
    report_markdown: Optional[str] = Field(None, description="Markdown格式完整报告")


class PsychologicalReportBrief(BaseSchema):
    """心理分析报告简要信息（用于列表）"""
    id: str
    session_id: str
    application_id: str
    overall_score: float
    risk_level: str
    created_at: datetime


# ========== Agent 输入/输出 Schema ==========

class PsychologicalAnalysisInput(BaseSchema):
    """心理分析 Agent 输入"""
    session_id: str
    application_id: str
    candidate_name: Optional[str] = None
    position_title: Optional[str] = None
    
    # 面试统计
    duration_seconds: float = 0
    utterance_count: Dict[str, int] = Field(default_factory=dict)
    char_count: Dict[str, int] = Field(default_factory=dict)
    speaking_ratio: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    
    # 心理数据汇总
    big_five_average: Dict[str, float] = Field(default_factory=dict)
    depression_average: Dict[str, Any] = Field(default_factory=dict)
    
    # 完整会话记录
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)


class PsychologicalAnalysisOutput(BaseSchema):
    """心理分析 Agent 输出"""
    big_five_analysis: BigFiveAnalysis
    deception_analysis: DeceptionAnalysis
    depression_analysis: DepressionAnalysis
    speech_pattern_analysis: SpeechPatternAnalysis
    
    overall_score: float = Field(..., ge=0, le=100, description="综合评分")
    risk_level: str = Field(..., description="风险等级")
    overall_summary: str = Field(..., description="综合评估摘要")
    recommendations: List[str] = Field(..., description="建议列表")
    report_markdown: str = Field(..., description="Markdown格式完整报告")
