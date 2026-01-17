"""
沉浸式面试会话 CRUD 操作
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.models.immersive import ImmersiveSession
from app.models.application import Application
from app.schemas.immersive import (
    ImmersiveSessionCreate, 
    ImmersiveSessionUpdate,
    TranscriptCreate,
    SpeakerSegmentCreate,
    StateRecordCreate,
    SyncDataRequest
)
from .base import CRUDBase


class CRUDImmersive(CRUDBase[ImmersiveSession]):
    """沉浸式面试会话 CRUD 操作类"""
    
    # ========== 基础查询方法 ==========
    
    async def get_with_application(
        self,
        db: AsyncSession,
        id: str
    ) -> Optional[ImmersiveSession]:
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
    ) -> Optional[ImmersiveSession]:
        """获取某申请的沉浸式面试会话（1:1关系）"""
        result = await db.execute(
            select(self.model)
            .where(self.model.application_id == application_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_status(
        self,
        db: AsyncSession,
        is_recording: Optional[bool] = None,
        is_completed: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ImmersiveSession]:
        """按状态筛选会话"""
        query = select(self.model)
        
        conditions = []
        if is_recording is not None:
            conditions.append(self.model.is_recording == is_recording)
        if is_completed is not None:
            conditions.append(self.model.is_completed == is_completed)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(self.model.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())
    
    # ========== 统计方法 ==========
    
    async def count_by_status(
        self,
        db: AsyncSession,
        is_completed: Optional[bool] = None
    ) -> int:
        """按状态统计会话数量"""
        query = select(func.count()).select_from(self.model)
        if is_completed is not None:
            query = query.where(self.model.is_completed == is_completed)
        
        result = await db.execute(query)
        return result.scalar() or 0
    
    async def count_active(self, db: AsyncSession) -> int:
        """统计活跃会话数量（正在录制）"""
        return await self.count_by_status(db, is_completed=False)
    
    # ========== 会话管理方法 ==========
    
    async def create_session(
        self,
        db: AsyncSession,
        *,
        obj_in: ImmersiveSessionCreate
    ) -> ImmersiveSession:
        """创建沉浸式面试会话"""
        return await self.create(db, obj_in=obj_in.model_dump())
    
    async def update_session(
        self,
        db: AsyncSession,
        *,
        db_obj: ImmersiveSession,
        obj_in: ImmersiveSessionUpdate
    ) -> ImmersiveSession:
        """更新会话"""
        update_data = obj_in.model_dump(exclude_unset=True)
        return await self.update(db, db_obj=db_obj, obj_in=update_data)
    
    # ========== 会话状态控制 ==========
    
    async def start_recording(
        self,
        db: AsyncSession,
        session_id: str
    ) -> ImmersiveSession:
        """开始录制"""
        session = await self.get(db, session_id)
        if not session:
            raise ValueError(f"会话不存在: {session_id}")
        
        session.is_recording = True
        session.start_time = datetime.now()
        await db.flush()
        await db.refresh(session)
        return session
    
    async def stop_recording(
        self,
        db: AsyncSession,
        session_id: str
    ) -> ImmersiveSession:
        """停止录制"""
        session = await self.get(db, session_id)
        if not session:
            raise ValueError(f"会话不存在: {session_id}")
        
        session.is_recording = False
        session.end_time = datetime.now()
        
        # 计算时长
        if session.start_time:
            session.duration_seconds = (session.end_time - session.start_time).total_seconds()
        
        await db.flush()
        await db.refresh(session)
        return session
    
    async def complete_session(
        self,
        db: AsyncSession,
        session_id: str
    ) -> ImmersiveSession:
        """完成会话"""
        session = await self.get(db, session_id)
        if not session:
            raise ValueError(f"会话不存在: {session_id}")
        
        session.is_recording = False
        session.is_completed = True
        
        if not session.end_time:
            session.end_time = datetime.now()
        
        # 计算时长
        if session.start_time and session.end_time:
            session.duration_seconds = (session.end_time - session.start_time).total_seconds()
        
        # 计算统计数据
        self._calculate_statistics(session)
        
        await db.flush()
        await db.refresh(session)
        return session
    
    # ========== 实时数据管理 ==========
    
    async def add_transcript(
        self,
        db: AsyncSession,
        session_id: str,
        transcript_data: TranscriptCreate
    ) -> ImmersiveSession:
        """添加转录记录"""
        session = await self.get(db, session_id)
        if not session:
            raise ValueError(f"会话不存在: {session_id}")
        
        # 准备转录数据
        transcript = {
            "speaker": transcript_data.speaker,
            "text": transcript_data.text,
            "timestamp": datetime.now().isoformat(),
            "is_final": transcript_data.is_final
        }
        
        # 添加到转录列表
        if session.transcripts is None:
            session.transcripts = []
        session.transcripts.append(transcript)
        
        # 标记字段已修改
        flag_modified(session, "transcripts")
        await db.flush()
        await db.refresh(session)
        return session
    
    async def add_speaker_segment(
        self,
        db: AsyncSession,
        session_id: str,
        segment_data: SpeakerSegmentCreate
    ) -> ImmersiveSession:
        """添加说话人分段"""
        session = await self.get(db, session_id)
        if not session:
            raise ValueError(f"会话不存在: {session_id}")
        
        # 准备分段数据
        segment = {
            "speaker": segment_data.speaker,
            "start_time": segment_data.start_time,
            "end_time": segment_data.end_time,
            "duration": segment_data.end_time - segment_data.start_time,
            "text": segment_data.text,
            "confidence": segment_data.confidence
        }
        
        # 添加心理分析数据（仅候选人）
        if segment_data.speaker == "candidate":
            if segment_data.big_five_personality:
                segment["big_five_personality"] = segment_data.big_five_personality.model_dump()
            if segment_data.depression_risk:
                segment["depression_risk"] = segment_data.depression_risk.model_dump()
            if segment_data.speech_features:
                segment["speech_features"] = segment_data.speech_features.model_dump()
        
        # 添加到分段列表
        if session.speaker_segments is None:
            session.speaker_segments = []
        session.speaker_segments.append(segment)
        
        # 标记字段已修改
        flag_modified(session, "speaker_segments")
        await db.flush()
        await db.refresh(session)
        return session
    
    async def add_state_record(
        self,
        db: AsyncSession,
        session_id: str,
        state_data: StateRecordCreate
    ) -> ImmersiveSession:
        """添加状态记录"""
        session = await self.get(db, session_id)
        if not session:
            raise ValueError(f"会话不存在: {session_id}")
        
        # 准备状态数据
        state = {
            "timestamp": datetime.now().isoformat(),
            "segment_id": state_data.segment_id,
            "emotion": state_data.emotion.model_dump(),
            "engagement": state_data.engagement,
            "nervousness": state_data.nervousness,
            "confidence_level": state_data.confidence_level,
            "eye_contact": state_data.eye_contact,
            "posture_score": state_data.posture_score,
            "speech_clarity": state_data.speech_clarity,
            "speech_pace": state_data.speech_pace
        }
        
        # 添加到状态历史
        if session.state_history is None:
            session.state_history = []
        session.state_history.append(state)
        
        # 标记字段已修改
        flag_modified(session, "state_history")
        await db.flush()
        await db.refresh(session)
        return session
    
    async def sync_realtime_data(
        self,
        db: AsyncSession,
        session_id: str,
        sync_data: SyncDataRequest
    ) -> ImmersiveSession:
        """批量同步实时数据"""
        session = await self.get(db, session_id)
        if not session:
            raise ValueError(f"会话不存在: {session_id}")
        
        # 同步转录数据
        if sync_data.transcripts:
            for transcript_data in sync_data.transcripts:
                await self.add_transcript(db, session_id, transcript_data)
        
        # 同步说话人分段
        if sync_data.speaker_segments:
            for segment_data in sync_data.speaker_segments:
                await self.add_speaker_segment(db, session_id, segment_data)
        
        # 同步状态记录
        if sync_data.state_records:
            for state_data in sync_data.state_records:
                await self.add_state_record(db, session_id, state_data)
        
        return session
    
    # ========== 统计和分析方法 ==========
    
    async def calculate_session_statistics(
        self,
        db: AsyncSession,
        session_id: str
    ) -> Dict[str, Any]:
        """计算会话统计数据"""
        session = await self.get(db, session_id)
        if not session:
            raise ValueError(f"会话不存在: {session_id}")
        
        return self._calculate_statistics(session)
    
    def _calculate_statistics(self, session: ImmersiveSession) -> Dict[str, Any]:
        """内部方法：计算统计数据"""
        stats = {
            "total_segments": session.segment_count,
            "candidate_segments": session.candidate_segments_count,
            "interviewer_segments": session.segment_count - session.candidate_segments_count,
            "candidate_speak_ratio": session.candidate_speak_ratio,
            "interviewer_speak_ratio": session.interviewer_speak_ratio,
            "session_quality_score": session.session_quality_score
        }
        
        # 计算平均指标
        if session.state_history:
            total_states = len(session.state_history)
            stats.update({
                "avg_engagement": sum(s.get("engagement", 0) for s in session.state_history) / total_states,
                "avg_confidence": sum(s.get("confidence_level", 0) for s in session.state_history) / total_states,
                "avg_nervousness": sum(s.get("nervousness", 0) for s in session.state_history) / total_states,
            })
        else:
            stats.update({
                "avg_engagement": 0,
                "avg_confidence": 0,
                "avg_nervousness": 0,
            })
        
        # 更新会话统计字段
        session.avg_engagement = stats["avg_engagement"]
        session.avg_confidence = stats["avg_confidence"]
        session.avg_nervousness = stats["avg_nervousness"]
        
        return stats
    
    async def generate_psychological_summary(
        self,
        db: AsyncSession,
        session_id: str
    ) -> Dict[str, Any]:
        """生成心理分析汇总"""
        session = await self.get(db, session_id)
        if not session:
            raise ValueError(f"会话不存在: {session_id}")
        
        summary = {
            "final_big_five": session.final_big_five,
            "depression_assessment": session.depression_assessment,
            "psychological_wellness_score": session.psychological_wellness_score,
            "trend_analysis": {
                "depression_risk_trend": session.get_depression_risk_trend(),
                "latest_state": session.get_latest_psychological_state()
            }
        }
        
        return summary
    
    async def get_session_summary(
        self,
        db: AsyncSession,
        session_id: str
    ) -> Dict[str, Any]:
        """获取完整会话汇总"""
        session = await self.get_with_application(db, session_id)
        if not session:
            raise ValueError(f"会话不存在: {session_id}")
        
        # 基础会话信息
        session_info = {
            "id": session.id,
            "duration_seconds": session.duration_seconds,
            "start_time": session.start_time.isoformat() if session.start_time else None,
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "is_completed": session.is_completed
        }
        
        # 统计数据
        statistics = self._calculate_statistics(session)
        
        # 心理分析汇总
        psychological_summary = await self.generate_psychological_summary(db, session_id)
        
        # 关联信息
        candidate_info = {}
        if session.application:
            if session.application.resume:
                candidate_info["name"] = session.application.resume.candidate_name
            if session.application.position:
                candidate_info["position_title"] = session.application.position.title
        
        return {
            "session_info": session_info,
            "statistics": statistics,
            "psychological_summary": psychological_summary,
            "candidate_info": candidate_info,
            "transcripts": session.transcripts or [],
            "speaker_segments": session.speaker_segments or [],
            "state_history": session.state_history or []
        }


# 创建 CRUD 实例
immersive_crud = CRUDImmersive(ImmersiveSession)