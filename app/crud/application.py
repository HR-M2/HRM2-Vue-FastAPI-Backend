"""
应聘申请 CRUD 操作 - SQLModel 简化版

只保留有价值的业务查询，通用 CRUD 直接使用基类方法
"""
from typing import Optional, List
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Application
from .base import CRUDBase


class CRUDApplication(CRUDBase[Application]):
    """
    应聘申请 CRUD 操作类
    
    通用方法直接使用基类：
    - get(db, id) / get_multi(db, skip, limit) / count(db)
    - create(db, obj_in) / update(db, db_obj, obj_in) / delete(db, id)
    """
    
    async def get_with_relations(self, db: AsyncSession, id: str) -> Optional[Application]:
        """获取申请详情（含所有关联数据），排除软删除"""
        result = await db.execute(
            select(self.model)
            .options(
                selectinload(self.model.position),
                selectinload(self.model.resume),
                selectinload(self.model.screening_task),
                selectinload(self.model.video_analysis),
                selectinload(self.model.interview_session),
                selectinload(self.model.comprehensive_analysis),
            )
            .where(and_(self.model.id == id, self.model.is_deleted == False))
        )
        return result.scalar_one_or_none()
    
    async def get_by_position(
        self,
        db: AsyncSession,
        position_id: str,
        *,
        skip: int = 0,
        limit: int = 100,
        include_details: bool = False
    ) -> List[Application]:
        """获取某岗位的所有申请，排除软删除"""
        if include_details:
            query = select(self.model).options(
                selectinload(self.model.position),
                selectinload(self.model.resume),
                selectinload(self.model.screening_task),
                selectinload(self.model.interview_session),
                selectinload(self.model.video_analysis),
                selectinload(self.model.comprehensive_analysis),
            )
        else:
            query = select(self.model).options(
                selectinload(self.model.position),
                selectinload(self.model.resume),
                selectinload(self.model.screening_task),
            )
        
        result = await db.execute(
            query
            .where(and_(
                self.model.position_id == position_id,
                self.model.is_deleted == False
            ))
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_resume(
        self,
        db: AsyncSession,
        resume_id: str,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[Application]:
        """获取某简历的所有申请，排除软删除"""
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.position))
            .where(and_(
                self.model.resume_id == resume_id,
                self.model.is_deleted == False
            ))
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def count_by_position(self, db: AsyncSession, position_id: str) -> int:
        """统计某岗位的申请数量，排除软删除"""
        result = await db.execute(
            select(func.count())
            .select_from(self.model)
            .where(and_(
                self.model.position_id == position_id,
                self.model.is_deleted == False
            ))
        )
        return result.scalar() or 0
    
    async def exists(
        self,
        db: AsyncSession,
        position_id: str,
        resume_id: str
    ) -> bool:
        """检查是否已存在相同的申请（未被软删除）"""
        result = await db.execute(
            select(self.model.id)
            .where(and_(
                self.model.position_id == position_id,
                self.model.resume_id == resume_id,
                self.model.is_deleted == False
            ))
        )
        return result.scalar_one_or_none() is not None
    
    async def get_deleted(
        self,
        db: AsyncSession,
        position_id: str,
        resume_id: str
    ) -> Optional[Application]:
        """获取已软删除的申请记录（用于恢复）"""
        result = await db.execute(
            select(self.model)
            .where(and_(
                self.model.position_id == position_id,
                self.model.resume_id == resume_id,
                self.model.is_deleted == True
            ))
        )
        return result.scalar_one_or_none()
    
    async def restore(self, db: AsyncSession, *, db_obj: Application) -> Application:
        """恢复已软删除的申请"""
        db_obj.is_deleted = False
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
    
    async def soft_delete(self, db: AsyncSession, id: str) -> bool:
        """软删除 - 业务逻辑"""
        obj = await self.get(db, id)
        if obj:
            obj.is_deleted = True
            await db.flush()
            await db.refresh(obj)
            return True
        return False
    
    async def get_list_with_relations(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[Application]:
        """获取申请列表（含基本关联数据），排除软删除"""
        result = await db.execute(
            select(self.model)
            .options(
                selectinload(self.model.position),
                selectinload(self.model.resume),
                selectinload(self.model.screening_task),
            )
            .where(self.model.is_deleted == False)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


application_crud = CRUDApplication(Application)
