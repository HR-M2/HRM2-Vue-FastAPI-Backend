"""
Schema 基类模块
"""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Schema 基类"""
    
    model_config = ConfigDict(
        from_attributes=True,  # 支持从 ORM 模型转换
        populate_by_name=True,  # 支持别名填充
        str_strip_whitespace=True,  # 自动去除字符串首尾空格
    )


class TimestampSchema(BaseSchema):
    """带时间戳的 Schema 基类"""
    
    id: str
    created_at: datetime
    updated_at: datetime
