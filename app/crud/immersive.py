"""
沉浸式面试会话 CRUD 操作
"""
import logging
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
    SyncDataRequest,
    SimplifiedSyncRequest,
    UtteranceCreate,
)
from .base import CRUDBase

logger = logging.getLogger(__name__)


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
        """获取某申请的沉浸式面试会话（如有多条返回最新一条）"""
        result = await db.execute(
            select(self.model)
            .options(
                selectinload(self.model.application)
                .selectinload(Application.position),
                selectinload(self.model.application)
                .selectinload(Application.resume),
            )
            .where(self.model.application_id == application_id)
            .order_by(self.model.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_completed_by_application(
        self,
        db: AsyncSession,
        application_id: str
    ) -> Optional[ImmersiveSession]:
        """获取某申请已完成的沉浸式面试会话（如有多条返回最新一条，用于综合分析）"""
        result = await db.execute(
            select(self.model)
            .options(
                selectinload(self.model.application)
                .selectinload(Application.position),
                selectinload(self.model.application)
                .selectinload(Application.resume),
            )
            .where(
                self.model.application_id == application_id,
                self.model.is_completed == True
            )
            .order_by(self.model.created_at.desc())
            .limit(1)
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
        """按状态筛选会话（预加载关联关系）"""
        query = select(self.model).options(
            selectinload(self.model.application)
            .selectinload(Application.position),
            selectinload(self.model.application)
            .selectinload(Application.resume),
        )
        
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

        start_time = float(segment_data.start_time)
        end_time = float(segment_data.end_time)
        if start_time > 1e10:
            start_time = start_time / 1000.0
        if end_time > 1e10:
            end_time = end_time / 1000.0
        
        # 准备分段数据
        segment = {
            "speaker": segment_data.speaker,
            "start_time": start_time,
            "end_time": end_time,
            "duration": max(0.0, end_time - start_time),
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
        """批量同步实时数据（旧版，保留兼容）"""
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
        
        # 同步状态记录（已废弃）
        if sync_data.state_records:
            for state_data in sync_data.state_records:
                await self.add_state_record(db, session_id, state_data)
        
        return session
    
    async def sync_utterances(
        self,
        db: AsyncSession,
        session_id: str,
        sync_data: SimplifiedSyncRequest
    ) -> ImmersiveSession:
        """简化的同步方法：同步发言记录（带三项心理评分）"""
        session = await self.get(db, session_id)
        if not session:
            raise ValueError(f"会话不存在: {session_id}")
        
        if session.speaker_segments is None:
            session.speaker_segments = []
        if session.transcripts is None:
            session.transcripts = []
        
        for utterance in sync_data.utterances:
            # 时间戳处理：毫秒转秒
            timestamp = float(utterance.timestamp)
            if timestamp > 1e10:
                timestamp = timestamp / 1000.0
            
            # 构建 speaker_segment 数据（主存储）
            segment = {
                "speaker": utterance.speaker,
                "text": utterance.text,
                "timestamp": timestamp,
            }
            
            # 添加候选人心理评分（不管 speaker 是谁都记录）
            if utterance.candidate_scores:
                scores = utterance.candidate_scores
                segment["candidate_scores"] = {}
                if scores.big_five:
                    segment["candidate_scores"]["big_five"] = scores.big_five.model_dump()
                if scores.deception:
                    segment["candidate_scores"]["deception"] = scores.deception.model_dump()
                if scores.depression:
                    segment["candidate_scores"]["depression"] = scores.depression.model_dump()
            
            session.speaker_segments.append(segment)
            
            # 同时写入 transcripts（简化版，兼容问题生成）
            transcript = {
                "speaker": utterance.speaker,
                "text": utterance.text,
                "timestamp": datetime.fromtimestamp(timestamp).isoformat(),
                "is_final": True
            }
            session.transcripts.append(transcript)
        
        flag_modified(session, "speaker_segments")
        flag_modified(session, "transcripts")
        await db.flush()
        await db.refresh(session)
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
        """获取完整会话汇总（旧版，保留兼容）"""
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
    
    async def get_simplified_complete_data(
        self,
        db: AsyncSession,
        session_id: str
    ) -> Dict[str, Any]:
        """获取简化的完成数据（重构后的新方法）"""
        session = await self.get_with_application(db, session_id)
        if not session:
            raise ValueError(f"会话不存在: {session_id}")
        
        speaker_segments = session.speaker_segments or []
        
        # ========== 发言次数统计 ==========
        total_utterances = len(speaker_segments)
        interviewer_utterances = sum(1 for s in speaker_segments if s.get("speaker") == "interviewer")
        candidate_utterances = sum(1 for s in speaker_segments if s.get("speaker") == "candidate")
        
        # ========== 字数统计 ==========
        interviewer_chars = sum(len(s.get("text", "")) for s in speaker_segments if s.get("speaker") == "interviewer")
        candidate_chars = sum(len(s.get("text", "")) for s in speaker_segments if s.get("speaker") == "candidate")
        total_chars = interviewer_chars + candidate_chars
        
        # ========== 发言占比（按次数） ==========
        interviewer_ratio_by_count = interviewer_utterances / total_utterances if total_utterances > 0 else 0
        candidate_ratio_by_count = candidate_utterances / total_utterances if total_utterances > 0 else 0
        
        # ========== 发言占比（按字数） ==========
        interviewer_ratio_by_chars = interviewer_chars / total_chars if total_chars > 0 else 0
        candidate_ratio_by_chars = candidate_chars / total_chars if total_chars > 0 else 0
        
        # ========== 大五人格平均值 ==========
        big_five_scores = {
            "openness": [],
            "conscientiousness": [],
            "extraversion": [],
            "agreeableness": [],
            "neuroticism": []
        }
        for seg in speaker_segments:
            scores = seg.get("candidate_scores", {})
            if scores and scores.get("big_five"):
                bf = scores["big_five"]
                for dim in big_five_scores:
                    if dim in bf and bf[dim] is not None:
                        big_five_scores[dim].append(bf[dim])
        
        big_five_average = {}
        for dim, values in big_five_scores.items():
            big_five_average[dim] = round(sum(values) / len(values), 4) if values else 0.5
        
        # ========== 抑郁水平平均值 ==========
        depression_scores = []
        for seg in speaker_segments:
            scores = seg.get("candidate_scores", {})
            if scores and scores.get("depression"):
                depression_scores.append(scores["depression"].get("score", 0))
        
        avg_depression = sum(depression_scores) / len(depression_scores) if depression_scores else 0
        if avg_depression < 30:
            depression_level = "low"
        elif avg_depression < 60:
            depression_level = "medium"
        else:
            depression_level = "high"
        
        depression_average = {
            "score": round(avg_depression, 2),
            "level": depression_level
        }
        
        # ========== 构建统计数据 ==========
        statistics = {
            "utterance_count": {
                "total": total_utterances,
                "interviewer": interviewer_utterances,
                "candidate": candidate_utterances
            },
            "char_count": {
                "total": total_chars,
                "interviewer": interviewer_chars,
                "candidate": candidate_chars
            },
            "speaking_ratio": {
                "by_count": {
                    "interviewer": round(interviewer_ratio_by_count, 4),
                    "candidate": round(candidate_ratio_by_count, 4)
                },
                "by_chars": {
                    "interviewer": round(interviewer_ratio_by_chars, 4),
                    "candidate": round(candidate_ratio_by_chars, 4)
                }
            },
            "big_five_average": big_five_average,
            "depression_average": depression_average
        }
        
        # 构建会话历史（每条记录捆绑三项评分）
        conversation_history = []
        for seg in speaker_segments:
            timestamp = seg.get("timestamp", 0)
            # 将时间戳转为ISO格式
            if isinstance(timestamp, (int, float)):
                ts_str = datetime.fromtimestamp(timestamp).isoformat()
            else:
                ts_str = str(timestamp)
            
            item = {
                "speaker": seg.get("speaker"),
                "text": seg.get("text", ""),
                "timestamp": ts_str,
                "candidate_scores": seg.get("candidate_scores")
            }
            conversation_history.append(item)
        
        # 候选人信息
        candidate_info = None
        if session.application:
            candidate_info = {}
            if session.application.resume:
                candidate_info["name"] = session.application.resume.candidate_name
            if session.application.position:
                candidate_info["position_title"] = session.application.position.title
        
        # 构建返回数据
        result = {
            "session_id": session.id,
            "duration_seconds": session.duration_seconds or 0,
            "start_time": session.start_time.isoformat() if session.start_time else None,
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "statistics": statistics,
            "conversation_history": conversation_history,
            "candidate_info": candidate_info
        }
        
        # 保存到 final_analysis 字段（供后续推荐使用）
        session.final_analysis = result
        flag_modified(session, "final_analysis")
        await db.flush()
        
        return result
    
    # ========== 问题建议方法 ==========
    
    async def generate_question_suggestions(
        self,
        db: AsyncSession,
        session_id: str,
        count: int = 5,
        difficulty: str = "medium",
        focus_areas: Optional[List[str]] = None,
        use_psychological_context: bool = True,
        use_conversation_history: bool = True,
        question_type: str = "mixed"
    ) -> List[Dict[str, Any]]:
        """生成智能问题建议（调用AI服务）"""
        from app.services.agents.immersive_interview_agent import get_immersive_interview_agent
        
        session = await self.get_with_application(db, session_id)
        if not session:
            raise ValueError(f"会话不存在: {session_id}")
        
        # 获取AI服务实例
        ai_agent = get_immersive_interview_agent()
        
        # 构建会话数据
        session_data = {
            "application": {
                "resume": {
                    "candidate_name": session.application.resume.candidate_name if session.application and session.application.resume else None,
                    "content": session.application.resume.content if session.application and session.application.resume else ""
                },
                "position": {
                    "title": session.application.position.title if session.application and session.application.position else None,
                    "required_skills": session.application.position.required_skills if session.application and session.application.position else [],
                    "description": session.application.position.description if session.application and session.application.position else ""
                }
            } if session.application else {},
            "transcripts": session.transcripts or []
        }
        
        # 构建上下文
        context = ai_agent.build_question_context(
            session_data, False, use_conversation_history
        )
        
        # 调用AI服务生成问题
        suggestions = await ai_agent.generate_question_suggestions(
            context, count, difficulty, focus_areas, question_type
        )
        
        return suggestions
    
    def _build_question_context(
        self, 
        session: ImmersiveSession, 
        use_psychological_context: bool,
        use_conversation_history: bool
    ) -> Dict[str, Any]:
        """构建问题生成的上下文信息（已废弃，迁移到AI服务层）"""
        # 这个方法已经迁移到 app.services.agents.immersive_interview_agent
        # 保留此方法是为了向后兼容，实际逻辑已移到AI服务层
        logger.warning("_build_question_context 方法已废弃，请使用 AI 服务层的方法")
        return {}


# 创建 CRUD 实例
immersive_crud = CRUDImmersive(ImmersiveSession)