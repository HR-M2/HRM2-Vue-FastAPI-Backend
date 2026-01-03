"""
面试会话 CRUD 操作 - SQLModel 简化版

只保留有价值的业务查询，通用 CRUD 直接使用基类方法
"""
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import InterviewSession, Application
from .base import CRUDBase


class CRUDInterview(CRUDBase[InterviewSession]):
    """
    面试会话 CRUD 操作类
    
    通用方法直接使用基类：
    - get(db, id) / get_multi(db, skip, limit) / count(db)
    - create(db, obj_in) / update(db, db_obj, obj_in) / delete(db, id)
    """
    
    async def get_with_application(self, db: AsyncSession, id: str) -> Optional[InterviewSession]:
        """获取面试会话（含申请信息）- 需要 selectinload"""
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
    
    async def get_by_application(self, db: AsyncSession, application_id: str) -> Optional[InterviewSession]:
        """根据申请ID获取面试会话（1:1关系）- 业务查询"""
        result = await db.execute(
            select(self.model).where(self.model.application_id == application_id)
        )
        return result.scalar_one_or_none()
    
    async def count_completed(self, db: AsyncSession) -> int:
        """统计已完成面试会话数量 - 带条件计数"""
        result = await db.execute(
            select(func.count())
            .select_from(self.model)
            .where(self.model.is_completed == True)
        )
        return result.scalar() or 0


interview_crud = CRUDInterview(InterviewSession)
