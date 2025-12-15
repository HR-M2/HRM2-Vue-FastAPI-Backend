"""
岗位相关 Schema
"""
from typing import Optional, List
from pydantic import Field

from .base import BaseSchema, TimestampSchema


class PositionBase(BaseSchema):
    """岗位基础字段"""
    
    title: str = Field(..., min_length=1, max_length=100, description="岗位名称")
    department: Optional[str] = Field(None, max_length=100, description="所属部门")
    description: Optional[str] = Field(None, description="岗位描述/JD")
    required_skills: Optional[List[str]] = Field(default_factory=list, description="必备技能")
    preferred_skills: Optional[List[str]] = Field(default_factory=list, description="优先技能")
    min_experience: int = Field(0, ge=0, description="最低工作年限")
    education_requirements: Optional[List[str]] = Field(default_factory=list, description="学历要求")
    salary_min: int = Field(0, ge=0, description="最低薪资(K)")
    salary_max: int = Field(0, ge=0, description="最高薪资(K)")


class PositionCreate(PositionBase):
    """创建岗位请求"""
    pass


class PositionUpdate(BaseSchema):
    """更新岗位请求"""
    
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    min_experience: Optional[int] = Field(None, ge=0)
    education_requirements: Optional[List[str]] = None
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class PositionResponse(TimestampSchema):
    """岗位响应"""
    
    title: str
    department: Optional[str]
    description: Optional[str]
    required_skills: List[str]
    preferred_skills: List[str]
    min_experience: int
    education_requirements: List[str]
    salary_min: int
    salary_max: int
    is_active: bool
    application_count: int = Field(0, description="申请数量")


class PositionListResponse(TimestampSchema):
    """岗位列表项响应（简化版）"""
    
    title: str
    department: Optional[str]
    is_active: bool
    application_count: int = 0
