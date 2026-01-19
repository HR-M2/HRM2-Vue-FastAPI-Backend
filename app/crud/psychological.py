"""
心理分析报告 CRUD 模块
"""
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.psychological import PsychologicalReport
from app.models.immersive import ImmersiveSession
from .base import CRUDBase


class CRUDPsychological(CRUDBase[PsychologicalReport]):
    """心理分析报告 CRUD"""
    
    async def get_by_session(
        self,
        db: AsyncSession,
        session_id: str
    ) -> Optional[PsychologicalReport]:
        """根据面试会话ID获取心理分析报告"""
        result = await db.execute(
            select(PsychologicalReport)
            .where(PsychologicalReport.session_id == session_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_application(
        self,
        db: AsyncSession,
        application_id: str
    ) -> Optional[PsychologicalReport]:
        """根据应聘申请ID获取最新的心理分析报告"""
        result = await db.execute(
            select(PsychologicalReport)
            .where(PsychologicalReport.application_id == application_id)
            .order_by(PsychologicalReport.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def create_or_update(
        self,
        db: AsyncSession,
        session_id: str,
        application_id: str,
        report_data: Dict[str, Any]
    ) -> PsychologicalReport:
        """
        创建或更新心理分析报告
        
        如果已存在则更新（覆盖），否则创建新报告
        """
        existing = await self.get_by_session(db, session_id)
        
        if existing:
            # 更新现有报告
            for key, value in report_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            await db.flush()
            await db.refresh(existing)
            return existing
        else:
            # 创建新报告
            report = PsychologicalReport(
                session_id=session_id,
                application_id=application_id,
                **report_data
            )
            db.add(report)
            await db.flush()
            await db.refresh(report)
            return report
    
    async def get_interview_data(
        self,
        db: AsyncSession,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取面试数据用于心理分析
        
        返回面试会话的统计数据和会话记录
        """
        result = await db.execute(
            select(ImmersiveSession)
            .options(
                selectinload(ImmersiveSession.application)
            )
            .where(ImmersiveSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            return None
        
        if not session.is_completed:
            return None
        
        # 从 final_analysis 获取已计算的数据
        final_analysis = session.final_analysis or {}
        statistics = final_analysis.get("statistics", {})
        conversation_history = final_analysis.get("conversation_history", [])
        
        # 获取候选人信息
        candidate_name = None
        position_title = None
        if session.application:
            # 需要加载 resume 和 position
            from app.crud.application import application_crud
            app_detail = await application_crud.get_detail(db, session.application_id)
            if app_detail:
                if app_detail.resume:
                    candidate_name = app_detail.resume.candidate_name
                if app_detail.position:
                    position_title = app_detail.position.title
        
        return {
            "session_id": session.id,
            "application_id": session.application_id,
            "candidate_name": candidate_name,
            "position_title": position_title,
            "duration_seconds": session.duration_seconds or 0,
            "utterance_count": statistics.get("utterance_count", {}),
            "char_count": statistics.get("char_count", {}),
            "speaking_ratio": statistics.get("speaking_ratio", {}),
            "big_five_average": statistics.get("big_five_average", {}),
            "depression_average": statistics.get("depression_average", {}),
            "conversation_history": conversation_history
        }
    
    async def delete_by_session(
        self,
        db: AsyncSession,
        session_id: str
    ) -> bool:
        """根据面试会话ID删除心理分析报告"""
        report = await self.get_by_session(db, session_id)
        if report:
            await db.delete(report)
            await db.flush()
            return True
        return False


# 创建 CRUD 实例
psychological_crud = CRUDPsychological(PsychologicalReport)
