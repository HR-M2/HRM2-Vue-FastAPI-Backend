"""
简历模型模块 - SQLModel 版本
"""
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

from .base import SQLModelBase, TimestampMixin, IDMixin, TimestampResponse

if TYPE_CHECKING:
    from .application import Application


# ==================== 基础字段定义 ====================

class ResumeBase(SQLModelBase):
    """简历基础字段"""
    candidate_name: str = Field(..., min_length=1, max_length=50, description="候选人姓名", index=True)
    phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    email: Optional[str] = Field(None, max_length=100, description="电子邮箱")
    content: str = Field(..., min_length=1, description="简历内容")
    filename: Optional[str] = Field(None, max_length=255, description="原始文件名")
    notes: Optional[str] = Field(None, description="备注")


# ==================== 表模型 ====================

class Resume(ResumeBase, TimestampMixin, IDMixin, table=True):
    """简历表模型"""
    __tablename__ = "resumes"
    
    file_hash: str = Field(..., max_length=64, unique=True, index=True, description="文件哈希(去重用)")
    file_size: int = Field(0, ge=0, description="文件大小(字节)")
    is_parsed: bool = Field(False, description="是否已解析")
    
    # 关联关系
    applications: List["Application"] = Relationship(
        back_populates="resume",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    
    def __repr__(self) -> str:
        return f"<Resume(id={self.id}, candidate={self.candidate_name})>"


# ==================== 请求 Schema ====================

class ResumeCreate(ResumeBase):
    """创建简历请求"""
    file_hash: str = Field(..., max_length=64, description="文件哈希")
    file_size: int = Field(0, ge=0, description="文件大小")


class ResumeUpdate(SQLModelBase):
    """更新简历请求"""
    candidate_name: Optional[str] = Field(None, min_length=1, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    content: Optional[str] = None
    notes: Optional[str] = None
    is_parsed: Optional[bool] = None


# ==================== 响应 Schema ====================

class ResumeResponse(TimestampResponse):
    """简历详情响应"""
    candidate_name: str
    phone: Optional[str]
    email: Optional[str]
    content: str
    filename: Optional[str]
    file_hash: str
    file_size: int
    is_parsed: bool
    notes: Optional[str]
    application_count: int = Field(0, description="申请数量")


class ResumeListResponse(TimestampResponse):
    """简历列表项响应（简化版）"""
    candidate_name: str
    phone: Optional[str]
    email: Optional[str]
    filename: Optional[str]
    is_parsed: bool
    application_count: int = 0
