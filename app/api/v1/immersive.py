"""
沉浸式面试 API 路由

提供双摄像头面试、说话人识别、实时状态分析等功能
"""
import random
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import (
    success_response,
    paged_response,
    ResponseModel,
    PagedResponseModel,
    MessageResponse,
    DictResponse,
)
from app.core.exceptions import NotFoundException, BadRequestException
from app.crud import application_crud
from app.schemas.immersive import (
    ImmersiveSessionCreate,
    ImmersiveSessionResponse,
    ImmersiveSessionUpdate,
    SpeakerDiarizationRequest,
    SpeakerDiarizationResponse,
    SpeakerSegment,
    StateAnalysisRequest,
    StateAnalysisResponse,
    CandidateState,
    EmotionState,
    QuestionSuggestion,
    InterviewInsight,
    RealtimeTranscript,
)

router = APIRouter()

# 内存存储（实验性功能，实际生产应使用数据库）
_immersive_sessions: dict = {}


def _generate_session_id() -> str:
    """生成会话ID"""
    import uuid
    return f"imm_{uuid.uuid4().hex[:12]}"


@router.post("", summary="创建沉浸式面试会话", response_model=DictResponse)
async def create_immersive_session(
    data: ImmersiveSessionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    创建新的沉浸式面试会话
    
    支持本地摄像头和远程推流双视图
    """
    # 验证应聘申请存在
    application = await application_crud.get_detail(db, data.application_id)
    if not application:
        raise NotFoundException(f"应聘申请不存在: {data.application_id}")
    
    session_id = _generate_session_id()
    
    session_data = {
        "id": session_id,
        "application_id": data.application_id,
        "local_camera_enabled": data.local_camera_enabled,
        "stream_url": data.stream_url,
        "config": data.config or {},
        "is_recording": False,
        "is_completed": False,
        "transcripts": [],
        "speaker_segments": [],
        "state_history": [],
        "duration_seconds": 0,
        "interviewer_speak_ratio": 0,
        "candidate_speak_ratio": 0,
        "final_analysis": None,
        "candidate_name": application.resume.candidate_name if application.resume else None,
        "position_title": application.position.title if application.position else None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "start_time": None,
    }
    
    _immersive_sessions[session_id] = session_data
    
    return success_response(
        data=session_data,
        message="沉浸式面试会话创建成功"
    )


@router.get("/{session_id}", summary="获取沉浸式会话详情", response_model=DictResponse)
async def get_immersive_session(
    session_id: str,
):
    """
    获取沉浸式面试会话详情
    """
    session = _immersive_sessions.get(session_id)
    if not session:
        raise NotFoundException(f"会话不存在: {session_id}")
    
    return success_response(data=session)


@router.post("/{session_id}/start", summary="开始面试", response_model=DictResponse)
async def start_immersive_session(
    session_id: str,
):
    """
    开始沉浸式面试录制
    """
    session = _immersive_sessions.get(session_id)
    if not session:
        raise NotFoundException(f"会话不存在: {session_id}")
    
    if session["is_completed"]:
        raise BadRequestException("会话已结束")
    
    session["is_recording"] = True
    session["start_time"] = datetime.now().isoformat()
    session["updated_at"] = datetime.now().isoformat()
    
    return success_response(
        data={"session_id": session_id, "status": "recording"},
        message="面试已开始"
    )


@router.post("/{session_id}/stop", summary="停止面试", response_model=DictResponse)
async def stop_immersive_session(
    session_id: str,
):
    """
    停止沉浸式面试录制
    """
    session = _immersive_sessions.get(session_id)
    if not session:
        raise NotFoundException(f"会话不存在: {session_id}")
    
    session["is_recording"] = False
    session["is_completed"] = True
    session["updated_at"] = datetime.now().isoformat()
    
    # 计算时长
    if session["start_time"]:
        start = datetime.fromisoformat(session["start_time"])
        session["duration_seconds"] = (datetime.now() - start).total_seconds()
    
    return success_response(
        data={"session_id": session_id, "status": "completed"},
        message="面试已结束"
    )


@router.post("/{session_id}/speaker-diarization", summary="说话人识别", response_model=DictResponse)
async def analyze_speaker_diarization(
    session_id: str,
    data: SpeakerDiarizationRequest,
):
    """
    分析音频片段的说话人
    
    返回说话人分段信息，区分面试官和候选人
    """
    session = _immersive_sessions.get(session_id)
    if not session:
        raise NotFoundException(f"会话不存在: {session_id}")
    
    # 模拟说话人识别结果（实际应调用AI服务）
    segments = []
    current_time = 0
    duration = data.duration
    
    while current_time < duration:
        speaker = "interviewer" if random.random() > 0.5 else "candidate"
        segment_duration = min(random.uniform(2, 8), duration - current_time)
        
        segments.append({
            "speaker": speaker,
            "start_time": current_time,
            "end_time": current_time + segment_duration,
            "text": f"[{speaker}说话内容...]",
            "confidence": random.uniform(0.85, 0.98)
        })
        
        current_time += segment_duration
    
    # 计算说话比例
    interviewer_time = sum(s["end_time"] - s["start_time"] for s in segments if s["speaker"] == "interviewer")
    candidate_time = sum(s["end_time"] - s["start_time"] for s in segments if s["speaker"] == "candidate")
    total_time = interviewer_time + candidate_time
    
    # 更新会话数据
    session["speaker_segments"].extend(segments)
    session["interviewer_speak_ratio"] = interviewer_time / total_time if total_time > 0 else 0
    session["candidate_speak_ratio"] = candidate_time / total_time if total_time > 0 else 0
    
    return success_response(data={
        "segments": segments,
        "total_interviewer_time": interviewer_time,
        "total_candidate_time": candidate_time,
        "interviewer_ratio": session["interviewer_speak_ratio"],
        "candidate_ratio": session["candidate_speak_ratio"],
    })


@router.post("/{session_id}/state-analysis", summary="候选人状态分析", response_model=DictResponse)
async def analyze_candidate_state(
    session_id: str,
    data: StateAnalysisRequest,
):
    """
    分析候选人当前状态
    
    基于视频帧和音频分析候选人的情绪、参与度、紧张程度等
    """
    session = _immersive_sessions.get(session_id)
    if not session:
        raise NotFoundException(f"会话不存在: {session_id}")
    
    # 模拟状态分析（实际应调用AI服务）
    emotions = ["neutral", "happy", "focused", "thinking", "nervous", "confident"]
    
    state = {
        "timestamp": datetime.now().isoformat(),
        "emotion": {
            "emotion": random.choice(emotions),
            "confidence": random.uniform(0.7, 0.95),
            "valence": random.uniform(-0.3, 0.8),
            "arousal": random.uniform(0.3, 0.7)
        },
        "engagement": random.uniform(0.6, 0.95),
        "nervousness": random.uniform(0.1, 0.5),
        "confidence_level": random.uniform(0.5, 0.9),
        "eye_contact": random.uniform(0.5, 0.95),
        "posture_score": random.uniform(0.6, 0.95),
        "speech_clarity": random.uniform(0.7, 0.95),
        "speech_pace": random.choice(["slow", "normal", "fast"])
    }
    
    # 生成建议
    suggestions = []
    alerts = []
    
    if state["nervousness"] > 0.4:
        suggestions.append("候选人略显紧张，可以适当放慢节奏或给予鼓励")
    if state["eye_contact"] < 0.6:
        alerts.append("候选人眼神接触较少，可能在回忆或思考")
    if state["engagement"] < 0.7:
        suggestions.append("参与度下降，建议切换话题或提出更有针对性的问题")
    if state["speech_pace"] == "fast":
        suggestions.append("候选人语速较快，可能是紧张或急于表达")
    
    # 更新会话
    session["state_history"].append(state)
    
    return success_response(data={
        "state": state,
        "suggestions": suggestions,
        "alerts": alerts
    })


@router.post("/{session_id}/transcript", summary="添加实时转录", response_model=DictResponse)
async def add_transcript(
    session_id: str,
    speaker: str = Query(..., description="说话人: interviewer/candidate"),
    text: str = Query(..., description="转录文本"),
    is_final: bool = Query(False, description="是否最终结果"),
):
    """
    添加实时语音转录文本
    """
    session = _immersive_sessions.get(session_id)
    if not session:
        raise NotFoundException(f"会话不存在: {session_id}")
    
    transcript = {
        "speaker": speaker,
        "text": text,
        "timestamp": datetime.now().isoformat(),
        "is_final": is_final
    }
    
    session["transcripts"].append(transcript)
    
    return success_response(data=transcript)


@router.get("/{session_id}/suggestions", summary="获取提问建议", response_model=DictResponse)
async def get_question_suggestions(
    session_id: str,
    context: Optional[str] = Query(None, description="当前上下文"),
):
    """
    基于面试进展获取智能提问建议
    """
    session = _immersive_sessions.get(session_id)
    if not session:
        raise NotFoundException(f"会话不存在: {session_id}")
    
    # 模拟问题建议（实际应调用AI服务）
    suggestions = [
        {
            "question": "您能详细描述一下在这个项目中遇到的最大技术挑战吗？",
            "type": "probe",
            "priority": 1,
            "reason": "深入了解技术能力"
        },
        {
            "question": "您是如何与团队其他成员协作完成这个任务的？",
            "type": "followup",
            "priority": 2,
            "reason": "考察团队协作能力"
        },
        {
            "question": "如果重新做这个项目，您会有什么不同的做法？",
            "type": "alternative",
            "priority": 3,
            "reason": "考察反思和学习能力"
        },
        {
            "question": "您对我们公司的产品有什么了解？有什么建议？",
            "type": "alternative",
            "priority": 4,
            "reason": "考察对公司的兴趣和准备程度"
        }
    ]
    
    return success_response(data={"suggestions": suggestions})


@router.get("/{session_id}/insights", summary="获取面试洞察", response_model=DictResponse)
async def get_interview_insights(
    session_id: str,
):
    """
    获取当前面试的实时洞察和分析
    """
    session = _immersive_sessions.get(session_id)
    if not session:
        raise NotFoundException(f"会话不存在: {session_id}")
    
    insights = []
    
    # 基于状态历史生成洞察
    if session["state_history"]:
        avg_engagement = sum(s["engagement"] for s in session["state_history"]) / len(session["state_history"])
        avg_nervousness = sum(s["nervousness"] for s in session["state_history"]) / len(session["state_history"])
        
        if avg_engagement > 0.8:
            insights.append({
                "category": "参与度",
                "content": "候选人整体参与度很高，对话题表现出浓厚兴趣",
                "severity": "info",
                "timestamp": datetime.now().isoformat()
            })
        
        if avg_nervousness > 0.4:
            insights.append({
                "category": "情绪状态",
                "content": "候选人整体紧张程度较高，建议营造更轻松的氛围",
                "severity": "warning",
                "timestamp": datetime.now().isoformat()
            })
    
    # 说话比例分析
    if session["interviewer_speak_ratio"] > 0.6:
        insights.append({
            "category": "对话平衡",
            "content": "面试官说话时间较长，建议给候选人更多表达机会",
            "severity": "warning",
            "timestamp": datetime.now().isoformat()
        })
    
    return success_response(data={"insights": insights})


@router.post("/{session_id}/generate-report", summary="生成面试报告", response_model=DictResponse)
async def generate_interview_report(
    session_id: str,
):
    """
    生成沉浸式面试的综合报告
    """
    session = _immersive_sessions.get(session_id)
    if not session:
        raise NotFoundException(f"会话不存在: {session_id}")
    
    # 模拟报告生成
    report = {
        "summary": {
            "duration_minutes": session["duration_seconds"] / 60,
            "total_questions": len([t for t in session["transcripts"] if t["speaker"] == "interviewer"]),
            "interviewer_speak_ratio": session["interviewer_speak_ratio"],
            "candidate_speak_ratio": session["candidate_speak_ratio"],
        },
        "candidate_analysis": {
            "overall_impression": "积极、专业",
            "communication_score": random.uniform(70, 95),
            "technical_depth": random.uniform(65, 90),
            "cultural_fit": random.uniform(70, 95),
        },
        "behavioral_indicators": {
            "avg_engagement": sum(s["engagement"] for s in session["state_history"]) / len(session["state_history"]) if session["state_history"] else 0.75,
            "avg_confidence": sum(s["confidence_level"] for s in session["state_history"]) / len(session["state_history"]) if session["state_history"] else 0.7,
            "emotional_stability": "稳定" if session["state_history"] else "未知",
        },
        "recommendations": [
            "候选人沟通能力强，适合需要跨团队协作的岗位",
            "技术深度有待进一步考察，建议安排技术面试",
            "整体表现积极，推荐进入下一轮面试"
        ],
        "generated_at": datetime.now().isoformat()
    }
    
    session["final_analysis"] = report
    
    return success_response(data={"report": report})


@router.delete("/{session_id}", summary="删除沉浸式会话", response_model=MessageResponse)
async def delete_immersive_session(
    session_id: str,
):
    """
    删除沉浸式面试会话
    """
    if session_id not in _immersive_sessions:
        raise NotFoundException(f"会话不存在: {session_id}")
    
    del _immersive_sessions[session_id]
    return success_response(message="会话删除成功")
