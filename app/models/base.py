"""
SQLModel 基类模块

定义通用字段和混入类
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class SQLModelBase(SQLModel):
    """
    SQLModel 基类配置
    
    所有 Schema 类都应继承此类
    """
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "str_strip_whitespace": True,
    }


class TimestampMixin(SQLModel):
    """时间戳混入类 - 用于表模型"""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        description="更新时间"
    )


class IDMixin(SQLModel):
    """ID 混入类 - 用于表模型"""
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        description="主键ID"
    )


class TimestampResponse(SQLModelBase):
    """带时间戳的响应基类"""
    id: str
    created_at: datetime
    updated_at: datetime
