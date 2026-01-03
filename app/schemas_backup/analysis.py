"""
综合分析相关 Schema
"""
from typing import Optional, Dict, List
from pydantic import Field

from .base import BaseSchema, TimestampSchema


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
