"""
综合分析 CRUD 操作 - SQLModel 简化版

只保留有价值的业务查询，通用 CRUD 直接使用基类方法
"""
from typing import Optional, List, Union
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    ComprehensiveAnalysis, 
    ComprehensiveAnalysisCreate,
    RecommendationLevel,
    Application,
)
from .base import CRUDBase


class CRUDAnalysis(CRUDBase[ComprehensiveAnalysis]):
    """
    综合分析 CRUD 操作类
    
    通用方法直接使用基类：
    - get(db, id) / get_multi(db, skip, limit) / count(db)
    - create(db, obj_in) / update(db, db_obj, obj_in) / delete(db, id)
    """
    
    async def get_with_application(self, db: AsyncSession, id: str) -> Optional[ComprehensiveAnalysis]:
        """获取综合分析（含申请信息）- 需要 selectinload"""
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
    
    async def get_by_application(self, db: AsyncSession, application_id: str) -> Optional[ComprehensiveAnalysis]:
        """根据申请ID获取综合分析（1:1关系）- 业务查询"""
        result = await db.execute(
            select(self.model).where(self.model.application_id == application_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_recommendation(
        self,
        db: AsyncSession,
        recommendation_level: Union[str, RecommendationLevel],
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[ComprehensiveAnalysis]:
        """根据推荐等级获取列表（支持字符串或枚举）- 带条件筛选"""
        level_value = recommendation_level.value if isinstance(recommendation_level, RecommendationLevel) else recommendation_level
        result = await db.execute(
            select(self.model)
            .where(self.model.recommendation_level == level_value)
            .order_by(self.model.final_score.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def create_with_result(
        self,
        db: AsyncSession,
        *,
        obj_in: ComprehensiveAnalysisCreate,
        analysis_result: dict
    ) -> ComprehensiveAnalysis:
        """
        创建综合分析 - 合并 Create Schema 和 AI 分析结果
        
        这是业务方法，不是薄包装
        """
        data = obj_in.model_dump()
        data.update(analysis_result)
        return await self.create(db, obj_in=data)


analysis_crud = CRUDAnalysis(ComprehensiveAnalysis)
