"""
简历 CRUD 操作
"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.resume import Resume
from app.schemas.resume import ResumeCreate, ResumeUpdate
from .base import CRUDBase


class CRUDResume(CRUDBase[Resume]):
    """简历 CRUD 操作类"""
    
    async def get_with_applications(
        self,
        db: AsyncSession,
        id: str
    ) -> Optional[Resume]:
        """获取简历详情（含申请列表）"""
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.applications))
            .where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_hash(
        self,
        db: AsyncSession,
        file_hash: str
    ) -> Optional[Resume]:
        """根据文件哈希查找（去重用）"""
        result = await db.execute(
            select(self.model).where(self.model.file_hash == file_hash)
        )
        return result.scalar_one_or_none()
    
    async def get_by_candidate_name(
        self,
        db: AsyncSession,
        name: str,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[Resume]:
        """根据候选人姓名搜索"""
        result = await db.execute(
            select(self.model)
            .where(self.model.candidate_name.contains(name))
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def create_resume(
        self,
        db: AsyncSession,
        *,
        obj_in: ResumeCreate
    ) -> Resume:
        """创建简历"""
        return await self.create(db, obj_in=obj_in.model_dump())
    
    async def update_resume(
        self,
        db: AsyncSession,
        *,
        db_obj: Resume,
        obj_in: ResumeUpdate
    ) -> Resume:
        """更新简历"""
        update_data = obj_in.model_dump(exclude_unset=True)
        return await self.update(db, db_obj=db_obj, obj_in=update_data)
    
    async def check_hash_exists(
        self,
        db: AsyncSession,
        file_hash: str
    ) -> bool:
        """检查文件哈希是否已存在"""
        resume = await self.get_by_hash(db, file_hash)
        return resume is not None


resume_crud = CRUDResume(Resume)
