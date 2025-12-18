"""
应聘申请 CRUD 操作
"""
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from .base import CRUDBase


class CRUDApplication(CRUDBase[Application]):
    """应聘申请 CRUD 操作类"""
    
    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[Application]:
        """获取多条申请记录（预加载关联数据），排除软删除记录"""
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
    
    async def count(self, db: AsyncSession) -> int:
        """统计申请数量，排除软删除记录"""
        from sqlalchemy import func
        result = await db.execute(
            select(func.count())
            .select_from(self.model)
            .where(self.model.is_deleted == False)
        )
        return result.scalar() or 0
    
    async def get_detail(
        self,
        db: AsyncSession,
        id: str
    ) -> Optional[Application]:
        """获取申请详情（含所有关联数据），排除软删除记录"""
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
            .where(self.model.id == id, self.model.is_deleted == False)
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
        """获取某岗位的所有申请，排除软删除记录"""
        if include_details:
            result = await db.execute(
                select(self.model)
                .options(
                    selectinload(self.model.position),
                    selectinload(self.model.resume),
                    selectinload(self.model.screening_task),
                    selectinload(self.model.interview_session),
                    selectinload(self.model.video_analysis),
                    selectinload(self.model.comprehensive_analysis),
                )
                .where(self.model.position_id == position_id, self.model.is_deleted == False)
                .order_by(self.model.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
        else:
            result = await db.execute(
                select(self.model)
                .options(
                    selectinload(self.model.position),
                    selectinload(self.model.resume),
                    selectinload(self.model.screening_task),
                )
                .where(self.model.position_id == position_id, self.model.is_deleted == False)
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
        """获取某简历的所有申请，排除软删除记录"""
        result = await db.execute(
            select(self.model)
            .options(
                selectinload(self.model.position),
            )
            .where(self.model.resume_id == resume_id, self.model.is_deleted == False)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def count_by_position(
        self,
        db: AsyncSession,
        position_id: str
    ) -> int:
        """统计某岗位的申请数量，排除软删除记录"""
        result = await db.execute(
            select(func.count())
            .select_from(self.model)
            .where(self.model.position_id == position_id, self.model.is_deleted == False)
        )
        return result.scalar() or 0
    
    async def exists(
        self,
        db: AsyncSession,
        position_id: str,
        resume_id: str
    ) -> bool:
        """检查申请是否已存在（未被软删除）"""
        result = await db.execute(
            select(self.model)
            .where(
                self.model.position_id == position_id,
                self.model.resume_id == resume_id,
                self.model.is_deleted == False
            )
        )
        return result.scalar_one_or_none() is not None
    
    async def get_deleted(
        self,
        db: AsyncSession,
        position_id: str,
        resume_id: str
    ) -> Optional[Application]:
        """获取已软删除的申请记录"""
        result = await db.execute(
            select(self.model)
            .where(
                self.model.position_id == position_id,
                self.model.resume_id == resume_id,
                self.model.is_deleted == True
            )
        )
        return result.scalar_one_or_none()
    
    async def restore(
        self,
        db: AsyncSession,
        *,
        db_obj: Application
    ) -> Application:
        """恢复已软删除的申请"""
        db_obj.is_deleted = False
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
    
    async def create_application(
        self,
        db: AsyncSession,
        *,
        obj_in: ApplicationCreate
    ) -> Application:
        """创建申请"""
        return await self.create(db, obj_in=obj_in.model_dump())
    
    async def update_application(
        self,
        db: AsyncSession,
        *,
        db_obj: Application,
        obj_in: ApplicationUpdate
    ) -> Application:
        """更新申请"""
        update_data = obj_in.model_dump(exclude_unset=True)
        return await self.update(db, db_obj=db_obj, obj_in=update_data)
    
    async def soft_delete(
        self,
        db: AsyncSession,
        *,
        id: str
    ) -> bool:
        """软删除申请（设置 is_deleted=True）"""
        obj = await self.get(db, id)
        if obj:
            obj.is_deleted = True
            await db.flush()
            await db.refresh(obj)
            return True
        return False


application_crud = CRUDApplication(Application)
