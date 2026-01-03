"""
岗位模型模块 - SQLModel 版本

合并了 Model 和 Schema，减少代码重复
"""
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, JSON

from .base import SQLModelBase, TimestampMixin, IDMixin, TimestampResponse

if TYPE_CHECKING:
    from .application import Application


# ==================== 基础字段定义 ====================

class PositionBase(SQLModelBase):
    """岗位基础字段 - 用于创建和继承"""
    title: str = Field(..., min_length=1, max_length=100, description="岗位名称", index=True)
    department: Optional[str] = Field(None, max_length=100, description="所属部门")
    description: Optional[str] = Field(None, description="岗位描述/JD")
    required_skills: List[str] = Field(default_factory=list, sa_column=Column(JSON), description="必备技能")
    optional_skills: List[str] = Field(default_factory=list, sa_column=Column(JSON), description="可选技能")
    min_experience: int = Field(0, ge=0, description="最低工作年限")
    education: List[str] = Field(default_factory=list, sa_column=Column(JSON), description="学历要求")
    salary_min: int = Field(0, ge=0, description="最低薪资(K)")
    salary_max: int = Field(0, ge=0, description="最高薪资(K)")


# ==================== 表模型 ====================

class Position(PositionBase, TimestampMixin, IDMixin, table=True):
    """岗位表模型"""
    __tablename__ = "positions"
    
    is_active: bool = Field(default=True, index=True, description="是否启用")
    
    # 关联关系
    applications: List["Application"] = Relationship(
        back_populates="position",
        sa_relationship_kwargs={"lazy": "selectin", "passive_deletes": "all"}
    )
    
    def __repr__(self) -> str:
        return f"<Position(id={self.id}, title={self.title})>"


# ==================== 请求 Schema ====================

class PositionCreate(PositionBase):
    """创建岗位请求"""
    pass


class PositionUpdate(SQLModelBase):
    """更新岗位请求 - 所有字段可选"""
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    required_skills: Optional[List[str]] = None
    optional_skills: Optional[List[str]] = None
    min_experience: Optional[int] = Field(None, ge=0)
    education: Optional[List[str]] = None
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


# ==================== 响应 Schema ====================

class PositionResponse(TimestampResponse):
    """岗位详情响应"""
    title: str
    department: Optional[str]
    description: Optional[str]
    required_skills: List[str]
    optional_skills: List[str]
    min_experience: int
    education: List[str]
    salary_min: int
    salary_max: int
    is_active: bool
    application_count: int = Field(0, description="申请数量")


class PositionListResponse(TimestampResponse):
    """岗位列表项响应（简化版）"""
    title: str
    department: Optional[str]
    is_active: bool
    application_count: int = 0
