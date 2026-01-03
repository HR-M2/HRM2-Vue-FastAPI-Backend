"""
岗位模型模块
"""
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Text, Integer, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .application import Application


class Position(BaseModel):
    """
    岗位模型
    
    存储招聘岗位信息和筛选标准
    """
    __tablename__ = "positions"
    
    # ========== 基本信息 ==========
    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="岗位名称"
    )
    department: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="所属部门"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="岗位描述/JD"
    )
    
    # ========== 任职要求 ==========
    required_skills: Mapped[Optional[list]] = mapped_column(
        JSON,
        default=list,
        comment="必备技能列表"
    )
    optional_skills: Mapped[Optional[list]] = mapped_column(
        JSON,
        default=list,
        comment="可选技能列表"
    )
    min_experience: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="最低工作年限"
    )
    education: Mapped[Optional[list]] = mapped_column(
        JSON,
        default=list,
        comment="学历要求"
    )
    
    # ========== 薪资范围 ==========
    salary_min: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="最低薪资(K)"
    )
    salary_max: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="最高薪资(K)"
    )
    
    # ========== 状态 ==========
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
        comment="是否启用"
    )
    
    # ========== 关联关系 ==========
    applications: Mapped[List["Application"]] = relationship(
        "Application",
        back_populates="position",
        lazy="selectin",
        passive_deletes="all"  # 完全禁用ORM设置外键为NULL，让数据库CASCADE生效
    )
    
    def __repr__(self) -> str:
        return f"<Position(id={self.id}, title={self.title})>"
