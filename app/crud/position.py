"""
岗位 CRUD 操作
"""
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.position import Position
from app.schemas.position import PositionCreate, PositionUpdate
from .base import CRUDBase


class CRUDPosition(CRUDBase[Position]):
    """岗位 CRUD 操作类"""
    
    async def get_with_count(self, db: AsyncSession, id: str) -> Optional[Position]:
        """获取岗位详情（含申请数量）"""
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.applications))
            .where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_title(
        self,
        db: AsyncSession,
        title: str
    ) -> Optional[Position]:
        """根据岗位名称查找"""
        result = await db.execute(
            select(self.model).where(self.model.title == title)
        )
        return result.scalar_one_or_none()
    
    async def get_active_positions(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[Position]:
        """获取启用的岗位列表"""
        result = await db.execute(
            select(self.model)
            .where(self.model.is_active == True)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def count_active(self, db: AsyncSession) -> int:
        """获取启用岗位数量"""
        result = await db.execute(
            select(func.count())
            .select_from(self.model)
            .where(self.model.is_active == True)
        )
        return result.scalar() or 0
    
    async def create_position(
        self,
        db: AsyncSession,
        *,
        obj_in: PositionCreate
    ) -> Position:
        """创建岗位"""
        return await self.create(db, obj_in=obj_in.model_dump())
    
    async def update_position(
        self,
        db: AsyncSession,
        *,
        db_obj: Position,
        obj_in: PositionUpdate
    ) -> Position:
        """更新岗位"""
        update_data = obj_in.model_dump(exclude_unset=True)
        return await self.update(db, db_obj=db_obj, obj_in=update_data)


position_crud = CRUDPosition(Position)
