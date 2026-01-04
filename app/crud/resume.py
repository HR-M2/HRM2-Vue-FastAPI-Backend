"""
简历 CRUD 操作 - SQLModel 简化版

只保留有价值的业务查询，通用 CRUD 直接使用基类方法
"""
from typing import Optional, List, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Resume
from .base import CRUDBase


class CRUDResume(CRUDBase[Resume]):
    """
    简历 CRUD 操作类
    
    通用方法直接使用基类：
    - get(db, id) / get_multi(db, skip, limit) / count(db)
    - create(db, obj_in) / update(db, db_obj, obj_in) / delete(db, id)
    """
    
    async def get_with_applications(self, db: AsyncSession, id: str) -> Optional[Resume]:
        """获取简历详情（含申请列表）- 需要 selectinload"""
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.applications))
            .where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_hash(self, db: AsyncSession, file_hash: str) -> Optional[Resume]:
        """根据文件哈希查找（去重用）- 业务查询"""
        result = await db.execute(
            select(self.model).where(self.model.file_hash == file_hash)
        )
        return result.scalar_one_or_none()
    
    async def search_by_name(
        self,
        db: AsyncSession,
        name: str,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[Resume]:
        """根据候选人姓名搜索 - 模糊查询"""
        result = await db.execute(
            select(self.model)
            .where(self.model.candidate_name.contains(name))
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def check_hash_exists(self, db: AsyncSession, file_hash: str) -> bool:
        """检查文件哈希是否已存在 - 业务逻辑"""
        resume = await self.get_by_hash(db, file_hash)
        return resume is not None
    
    async def check_hashes_batch(
        self,
        db: AsyncSession,
        file_hashes: List[str]
    ) -> Dict[str, bool]:
        """批量检查文件哈希是否已存在 - 批量优化查询"""
        result = await db.execute(
            select(self.model.file_hash)
            .where(self.model.file_hash.in_(file_hashes))
        )
        existing = set(result.scalars().all())
        return {h: h in existing for h in file_hashes}
    
    async def delete_batch(self, db: AsyncSession, ids: List[str]) -> int:
        """批量删除简历 - 批量操作"""
        count = 0
        for id in ids:
            if await self.delete(db, id=id):
                count += 1
        return count


resume_crud = CRUDResume(Resume)
