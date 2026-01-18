"""
综合分析相关 Schema
"""
from typing import Optional, Dict, List
from pydantic import Field

from .base import BaseSchema, TimestampSchema


# ========== 心理分析相关模型 ==========

class BigFiveScores(BaseSchema):
    """大五人格评分"""
    openness: float = Field(0.5, ge=0, le=1, description="开放性")
    conscientiousness: float = Field(0.5, ge=0, le=1, description="尽责性")
    extraversion: float = Field(0.5, ge=0, le=1, description="外向性")
    agreeableness: float = Field(0.5, ge=0, le=1, description="宜人性")
    neuroticism: float = Field(0.5, ge=0, le=1, description="神经质")


class BigFiveAnalysis(BaseSchema):
    """大五人格分析结果"""
    scores: BigFiveScores = Field(default_factory=BigFiveScores, description="各维度平均评分")
    personality_summary: str = Field("", description="性格特点一句话概括")
    strengths: List[str] = Field(default_factory=list, description="性格优势")
    potential_concerns: List[str] = Field(default_factory=list, description="潜在关注点")
    work_style: str = Field("", description="工作风格")
    team_fit: str = Field("", description="团队协作倾向")
    detailed_analysis: str = Field("", description="详细分析")


class LowCredibilityResponse(BaseSchema):
    """低可信度回答"""
    text: str = Field("", description="回答内容")
    deception_score: float = Field(0, description="欺骗分数")
    confidence: float = Field(0, description="检测置信度")


class CredibilityAnalysis(BaseSchema):
    """可信度分析结果"""
    overall_score: float = Field(1.0, ge=0, le=1, description="整体可信度分数")
    level: str = Field("高可信度", description="可信度等级")
    low_credibility_responses: List[LowCredibilityResponse] = Field(default_factory=list, description="低可信度回答")
    high_credibility_responses: List[LowCredibilityResponse] = Field(default_factory=list, description="高可信度回答")
    analysis: str = Field("", description="分析说明")


class DepressionAnalysis(BaseSchema):
    """抑郁风险分析结果"""
    overall_score: float = Field(0, description="平均抑郁分数")
    level: str = Field("low", description="风险等级 low/medium/high")
    level_label: str = Field("低风险", description="风险等级标签")
    level_distribution: Optional[Dict[str, int]] = Field(None, description="各等级分布")
    interpretation: str = Field("", description="风险解读")


class PsychologicalAnalysis(BaseSchema):
    """心理分析汇总"""
    big_five: BigFiveAnalysis = Field(default_factory=BigFiveAnalysis, description="大五人格分析")
    credibility: CredibilityAnalysis = Field(default_factory=CredibilityAnalysis, description="可信度分析")
    depression: DepressionAnalysis = Field(default_factory=DepressionAnalysis, description="抑郁风险分析")


# ========== 维度评分模型 ==========

class DimensionScoreItem(BaseSchema):
    """
    单个维度评分项
    
    基于 evaluation_agents.py 中 _evaluate_dimension 方法的实际输出结构
    """
    dimension_score: Optional[int] = Field(None, ge=1, le=5, description="维度评分(1-5)")
    dimension_name: Optional[str] = Field(None, description="维度名称")
    weight: Optional[float] = Field(None, description="权重")
    sub_scores: Optional[Dict[str, int]] = Field(None, description="子维度评分")
    strengths: Optional[List[str]] = Field(None, description="优势列表")
    weaknesses: Optional[List[str]] = Field(None, description="不足列表")
    analysis: Optional[str] = Field(None, description="详细分析说明")


class ComprehensiveAnalysisCreate(BaseSchema):
    """创建综合分析请求"""
    
    application_id: str = Field(..., description="应聘申请ID")


class ComprehensiveAnalysisUpdate(BaseSchema):
    """更新综合分析请求"""
    
    final_score: Optional[float] = Field(None, ge=0, le=100, description="综合得分")
    recommendation_level: Optional[str] = Field(None, description="推荐等级")
    recommendation_reason: Optional[str] = Field(None, description="推荐理由")
    suggested_action: Optional[str] = Field(None, description="建议行动")
    dimension_scores: Optional[Dict] = Field(None, description="各维度评分")
    report: Optional[str] = Field(None, description="分析报告")
    input_snapshot: Optional[Dict] = Field(None, description="输入数据快照")


class ComprehensiveAnalysisResponse(TimestampSchema):
    """综合分析响应"""
    
    application_id: str
    final_score: float
    recommendation_level: str
    recommendation_reason: Optional[str]
    suggested_action: Optional[str]
    dimension_scores: Dict[str, DimensionScoreItem] = Field(default_factory=dict, description="各维度评分，key为维度ID")
    report: Optional[str]
    input_snapshot: Dict
    
    # 关联信息
    candidate_name: Optional[str] = None
    position_title: Optional[str] = None
