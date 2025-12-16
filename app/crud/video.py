"""
视频分析 CRUD 操作
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.video import VideoAnalysis
from app.schemas.video import VideoAnalysisCreate, VideoResultUpdate
from .base import CRUDBase


class CRUDVideo(CRUDBase[VideoAnalysis]):
    """视频分析 CRUD 操作类"""
    
    async def get_with_application(
        self,
        db: AsyncSession,
        id: str
    ) -> Optional[VideoAnalysis]:
        """获取视频分析详情（含申请信息）"""
        result = await db.execute(
            select(self.model)
            .options(
                selectinload(self.model.application)
                .selectinload("position"),
                selectinload(self.model.application)
                .selectinload("resume"),
            )
            .where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_application(
        self,
        db: AsyncSession,
        application_id: str
    ) -> Optional[VideoAnalysis]:
        """获取某申请的视频分析（1:1关系）"""
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
    ) -> list[VideoAnalysis]:
        """获取某状态的所有视频分析"""
        result = await db.execute(
            select(self.model)
            .where(self.model.status == status)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def create_video(
        self,
        db: AsyncSession,
        *,
        obj_in: VideoAnalysisCreate
    ) -> VideoAnalysis:
        """创建视频分析"""
        return await self.create(db, obj_in=obj_in.model_dump())
    
    async def update_result(
        self,
        db: AsyncSession,
        *,
        db_obj: VideoAnalysis,
        obj_in: VideoResultUpdate
    ) -> VideoAnalysis:
        """更新视频分析结果"""
        update_data = obj_in.model_dump(exclude_unset=True)
        return await self.update(db, db_obj=db_obj, obj_in=update_data)


video_crud = CRUDVideo(VideoAnalysis)
