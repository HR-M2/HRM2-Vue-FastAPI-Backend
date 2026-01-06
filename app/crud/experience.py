# -*- coding: utf-8 -*-
"""
Agent 经验 CRUD 模块

继承 CRUDBase，添加按类别查询的业务方法。
"""
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import CRUDBase
from app.models import AgentExperience


class CRUDExperience(CRUDBase[AgentExperience]):
    """Agent 经验 CRUD 操作"""
    
    async def get_by_category(
        self, 
        db: AsyncSession, 
        category: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AgentExperience]:
        """
        按类别获取经验列表
        
        Args:
            db: 数据库会话
            category: 经验类别 (screening/interview/analysis)
            skip: 跳过条数
            limit: 返回条数
            
        Returns:
            经验列表
        """
        result = await db.execute(
            select(self.model)
            .where(self.model.category == category)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_all_by_category(
        self, 
        db: AsyncSession, 
        category: str
    ) -> List[AgentExperience]:
        """
        获取某类别的所有经验（用于向量检索）
        
        Args:
            db: 数据库会话
            category: 经验类别
            
        Returns:
            经验列表
        """
        result = await db.execute(
            select(self.model)
            .where(self.model.category == category)
        )
        return list(result.scalars().all())
    
    async def count_by_category(
        self, 
        db: AsyncSession, 
        category: str
    ) -> int:
        """
        统计某类别的经验数量
        
        Args:
            db: 数据库会话
            category: 经验类别
            
        Returns:
            经验数量
        """
        from sqlalchemy import func
        result = await db.execute(
            select(func.count())
            .select_from(self.model)
            .where(self.model.category == category)
        )
        return result.scalar() or 0


# 单例实例
experience_crud = CRUDExperience(AgentExperience)
