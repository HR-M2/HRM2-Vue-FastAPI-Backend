"""
综合分析 CRUD 操作
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analysis import ComprehensiveAnalysis
from app.schemas.analysis import ComprehensiveAnalysisCreate, ComprehensiveAnalysisUpdate
from .base import CRUDBase


class CRUDAnalysis(CRUDBase[ComprehensiveAnalysis]):
    """综合分析 CRUD 操作类"""
    
    async def get_with_application(
        self,
        db: AsyncSession,
        id: str
    ) -> Optional[ComprehensiveAnalysis]:
        """获取分析详情（含申请信息）"""
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
    ) -> Optional[ComprehensiveAnalysis]:
        """获取某申请的综合分析（1:1关系）"""
        result = await db.execute(
            select(self.model)
            .where(self.model.application_id == application_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_recommendation(
        self,
        db: AsyncSession,
        recommendation_level: str,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> list[ComprehensiveAnalysis]:
        """获取某推荐等级的所有分析"""
        result = await db.execute(
            select(self.model)
            .where(self.model.recommendation_level == recommendation_level)
            .order_by(self.model.final_score.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def create_analysis(
        self,
        db: AsyncSession,
        *,
        obj_in: ComprehensiveAnalysisCreate,
        analysis_result: dict
    ) -> ComprehensiveAnalysis:
        """创建综合分析"""
        data = obj_in.model_dump()
        data.update(analysis_result)
        return await self.create(db, obj_in=data)
    
    async def update_analysis(
        self,
        db: AsyncSession,
        *,
        db_obj: ComprehensiveAnalysis,
        obj_in: ComprehensiveAnalysisUpdate
    ) -> ComprehensiveAnalysis:
        """更新综合分析"""
        update_data = obj_in.model_dump(exclude_unset=True)
        return await self.update(db, db_obj=db_obj, obj_in=update_data)


analysis_crud = CRUDAnalysis(ComprehensiveAnalysis)
