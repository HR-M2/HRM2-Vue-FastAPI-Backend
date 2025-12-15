"""
简历模型模块
"""
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Text, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .application import Application


class Resume(BaseModel):
    """
    简历模型
    
    存储候选人简历信息，一份简历可以投递多个岗位（多个 Application）
    """
    __tablename__ = "resumes"
    
    # ========== 候选人信息 ==========
    candidate_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="候选人姓名"
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="联系电话"
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="电子邮箱"
    )
    
    # ========== 简历内容 ==========
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="简历内容(文本)"
    )
    
    # ========== 文件信息 ==========
    filename: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="原始文件名"
    )
    file_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="文件哈希(去重用)"
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="文件大小(字节)"
    )
    
    # ========== 状态 ==========
    is_parsed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="是否已解析"
    )
    
    # ========== 备注 ==========
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="备注"
    )
    
    # ========== 关联关系 ==========
    applications: Mapped[List["Application"]] = relationship(
        "Application",
        back_populates="resume",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<Resume(id={self.id}, candidate={self.candidate_name})>"
