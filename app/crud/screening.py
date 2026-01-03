"""
筛选任务 CRUD 操作 - SQLModel 简化版

只保留有价值的业务查询，通用 CRUD 直接使用基类方法
"""
from typing import Optional, List, Union
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ScreeningTask, TaskStatus, Application
from .base import CRUDBase


class CRUDScreening(CRUDBase[ScreeningTask]):
    """
    筛选任务 CRUD 操作类
    
    通用方法直接使用基类：
    - get(db, id) / get_multi(db, skip, limit) / count(db)
    - create(db, obj_in) / update(db, db_obj, obj_in) / delete(db, id)
    """
    
    async def get_with_application(self, db: AsyncSession, id: str) -> Optional[ScreeningTask]:
        """获取筛选任务（含申请信息）- 需要 selectinload"""
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
    
    async def get_by_application(self, db: AsyncSession, application_id: str) -> Optional[ScreeningTask]:
        """根据申请ID获取筛选任务（1:1关系）- 业务查询"""
        result = await db.execute(
            select(self.model).where(self.model.application_id == application_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_status(
        self,
        db: AsyncSession,
        status: Union[str, TaskStatus],
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[ScreeningTask]:
        """根据状态获取任务列表（支持字符串或枚举）- 带条件筛选"""
        status_value = status.value if isinstance(status, TaskStatus) else status
        result = await db.execute(
            select(self.model)
            .where(self.model.status == status_value)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def count_by_status(self, db: AsyncSession, status: Union[str, TaskStatus]) -> int:
        """统计某状态的任务数量 - 带条件计数"""
        status_value = status.value if isinstance(status, TaskStatus) else status
        result = await db.execute(
            select(func.count())
            .select_from(self.model)
            .where(self.model.status == status_value)
        )
        return result.scalar() or 0
    
    async def get_list_with_details(
        self,
        db: AsyncSession,
        *,
        status: str = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ScreeningTask]:
        """获取任务列表（包含关联的申请、简历、岗位信息）- 复杂关联查询"""
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


screening_crud = CRUDScreening(ScreeningTask)
