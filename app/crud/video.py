"""
视频分析 CRUD 操作 - SQLModel 简化版

只保留有价值的业务查询，通用 CRUD 直接使用基类方法
"""
from typing import Optional, List, Union
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import VideoAnalysis, TaskStatus, Application
from .base import CRUDBase


class CRUDVideo(CRUDBase[VideoAnalysis]):
    """
    视频分析 CRUD 操作类
    
    通用方法直接使用基类：
    - get(db, id) / get_multi(db, skip, limit) / count(db)
    - create(db, obj_in) / update(db, db_obj, obj_in) / delete(db, id)
    """
    
    async def get_with_application(self, db: AsyncSession, id: str) -> Optional[VideoAnalysis]:
        """获取视频分析（含申请信息）- 需要 selectinload"""
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
    
    async def get_by_application(self, db: AsyncSession, application_id: str) -> Optional[VideoAnalysis]:
        """根据申请ID获取视频分析（1:1关系）- 业务查询"""
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
    ) -> List[VideoAnalysis]:
        """根据状态获取列表（支持字符串或枚举）- 带条件筛选"""
        status_value = status.value if isinstance(status, TaskStatus) else status
        result = await db.execute(
            select(self.model)
            .where(self.model.status == status_value)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


video_crud = CRUDVideo(VideoAnalysis)
