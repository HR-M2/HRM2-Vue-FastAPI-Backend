"""
面试会话 CRUD 操作
"""
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.interview import InterviewSession
from app.models.application import Application
from app.schemas.interview import InterviewSessionCreate, InterviewSessionUpdate
from .base import CRUDBase


class CRUDInterview(CRUDBase[InterviewSession]):
    """面试会话 CRUD 操作类"""
    
    async def get_with_application(
        self,
        db: AsyncSession,
        id: str
    ) -> Optional[InterviewSession]:
        """获取会话详情（含申请信息）"""
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
    
    async def get_by_application(
        self,
        db: AsyncSession,
        application_id: str
    ) -> Optional[InterviewSession]:
        """获取某申请的面试会话（1:1关系）"""
        result = await db.execute(
            select(self.model)
            .where(self.model.application_id == application_id)
        )
        return result.scalar_one_or_none()
    
    async def count_completed(
        self,
        db: AsyncSession
    ) -> int:
        """统计已完成面试会话数量"""
        result = await db.execute(
            select(func.count())
            .select_from(self.model)
            .where(self.model.is_completed == True)
        )
        return result.scalar() or 0
    
    async def create_session(
        self,
        db: AsyncSession,
        *,
        obj_in: InterviewSessionCreate
    ) -> InterviewSession:
        """创建面试会话"""
        return await self.create(db, obj_in=obj_in.model_dump())
    
    async def update_session(
        self,
        db: AsyncSession,
        *,
        db_obj: InterviewSession,
        obj_in: InterviewSessionUpdate
    ) -> InterviewSession:
        """更新面试会话"""
        update_data = obj_in.model_dump(exclude_unset=True)
        return await self.update(db, db_obj=db_obj, obj_in=update_data)
    
    async def add_qa_record(
        self,
        db: AsyncSession,
        *,
        db_obj: InterviewSession,
        question: str,
        answer: str,
        score: float = None,
        evaluation: str = None
    ) -> InterviewSession:
        """添加问答记录"""
        db_obj.add_qa_record(question, answer, score, evaluation)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


interview_crud = CRUDInterview(InterviewSession)
