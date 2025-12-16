"""
筛选任务 CRUD 操作
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.screening import ScreeningTask
from app.models.application import Application
from app.schemas.screening import ScreeningTaskCreate, ScreeningResultUpdate
from .base import CRUDBase


class CRUDScreening(CRUDBase[ScreeningTask]):
    """筛选任务 CRUD 操作类"""
    
    async def get_with_application(
        self,
        db: AsyncSession,
        id: str
    ) -> Optional[ScreeningTask]:
        """获取任务详情（含申请信息）"""
        result = await db.execute(
            select(self.model)
            .options(
                selectinload(self.model.application)
                .selectinload(Application.position),
                selectinload(self.model.application)
                .selectinload(Application.resume),
            )
            .where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_application(
        self,
        db: AsyncSession,
        application_id: str
    ) -> Optional[ScreeningTask]:
        """获取某申请的筛选任务（1:1关系）"""
        result = await db.execute(
            select(self.model)
            .where(self.model.application_id == application_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_status(
        self,
        db: AsyncSession,
        status: str,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> list[ScreeningTask]:
        """获取某状态的所有任务"""
        result = await db.execute(
            select(self.model)
            .where(self.model.status == status)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_list_with_details(
        self,
        db: AsyncSession,
        *,
        status: str = None,
        skip: int = 0,
        limit: int = 100
    ) -> list[ScreeningTask]:
        """获取任务列表（包含关联的申请、简历、岗位信息）"""
        query = select(self.model).options(
            selectinload(self.model.application)
            .selectinload(Application.resume),
            selectinload(self.model.application)
            .selectinload(Application.position),
        )
        
        if status:
            query = query.where(self.model.status == status)
        
        query = query.order_by(self.model.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def create_task(
        self,
        db: AsyncSession,
        *,
        obj_in: ScreeningTaskCreate
    ) -> ScreeningTask:
        """创建筛选任务"""
        return await self.create(db, obj_in=obj_in.model_dump())
    
    async def update_result(
        self,
        db: AsyncSession,
        *,
        db_obj: ScreeningTask,
        obj_in: ScreeningResultUpdate
    ) -> ScreeningTask:
        """更新筛选结果"""
        update_data = obj_in.model_dump(exclude_unset=True)
        return await self.update(db, db_obj=db_obj, obj_in=update_data)


screening_crud = CRUDScreening(ScreeningTask)
