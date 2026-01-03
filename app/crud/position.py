"""
岗位 CRUD 操作 - SQLModel 简化版

只保留有价值的业务查询，通用 CRUD 直接使用基类方法
"""
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Position
from .base import CRUDBase


class CRUDPosition(CRUDBase[Position]):
    """
    岗位 CRUD 操作类
    
    通用方法直接使用基类：
    - get(db, id) - 按 ID 获取
    - get_multi(db, skip, limit) - 分页获取
    - count(db) - 计数
    - create(db, obj_in) - 创建
    - update(db, db_obj, obj_in) - 更新
    - delete(db, id) - 删除
    """
    
    async def get_with_applications(self, db: AsyncSession, id: str) -> Optional[Position]:
        """获取岗位详情（含申请列表）- 需要 selectinload"""
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.applications))
            .where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_title(self, db: AsyncSession, title: str) -> Optional[Position]:
        """根据岗位名称查找 - 业务查询"""
        result = await db.execute(
            select(self.model).where(self.model.title == title)
        )
        return result.scalar_one_or_none()
    
    async def get_active(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[Position]:
        """获取启用的岗位列表 - 带条件筛选"""
        result = await db.execute(
            select(self.model)
            .where(self.model.is_active == True)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def count_active(self, db: AsyncSession) -> int:
        """获取启用岗位数量 - 带条件计数"""
        result = await db.execute(
            select(func.count())
            .select_from(self.model)
            .where(self.model.is_active == True)
        )
        return result.scalar() or 0


position_crud = CRUDPosition(Position)
