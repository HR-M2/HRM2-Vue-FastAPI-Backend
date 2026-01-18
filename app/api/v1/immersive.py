"""
沉浸式面试 API 路由

提供双摄像头面试、说话人识别、实时状态分析等功能
"""
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
from app.crud import immersive_crud, application_crud
from app.schemas.immersive import (
    ImmersiveSessionCreate,
    ImmersiveSessionResponse,
    ImmersiveSessionDetailResponse,
    ImmersiveSessionUpdate,
    SimplifiedSyncRequest,
    SyncDataRequest,
    TranscriptCreate,
    SpeakerSegmentCreate,
    StateRecordCreate,
    GenerateQuestionsRequest,
    QuestionSuggestionResponse,
)

router = APIRouter()


@router.get("", summary="获取沉浸式面试会话列表", response_model=PagedResponseModel[ImmersiveSessionResponse])
async def get_immersive_sessions(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    application_id: Optional[str] = Query(None, description="应聘申请ID"),
    is_recording: Optional[bool] = Query(None, description="是否正在录制"),
    is_completed: Optional[bool] = Query(None, description="是否已完成"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取沉浸式面试会话列表
    
    支持按应聘申请ID、录制状态、完成状态筛选
    """
    skip = (page - 1) * page_size
    
    if application_id:
        # 1:1 关系，直接获取单个会话
        session = await immersive_crud.get_by_application(db, application_id)
        sessions = [session] if session else []
        total = 1 if session else 0
    else:
        # 按状态筛选
        sessions = await immersive_crud.get_by_status(
            db, 
            is_recording=is_recording,
            is_completed=is_completed,
            skip=skip, 
            limit=page_size
        )
        total = await immersive_crud.count_by_status(db, is_completed=is_completed)
    
    items = []
    for s in sessions:
        # 手动构建响应字典，避免 model_validate 触发懒加载
        item = {
            "id": s.id,
            "application_id": s.application_id,
            "local_camera_enabled": s.local_camera_enabled,
            "stream_url": s.stream_url,
            "config": s.config or {},
            "is_recording": s.is_recording,
            "is_completed": s.is_completed,
            "transcripts": s.transcripts or [],
            "speaker_segments": s.speaker_segments or [],
            "state_history": s.state_history or [],
            "duration_seconds": s.duration_seconds or 0,
            "interviewer_speak_ratio": s.interviewer_speak_ratio or 0,
            "candidate_speak_ratio": s.candidate_speak_ratio or 0,
            "final_analysis": s.final_analysis,
            "candidate_name": None,
            "position_title": None,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }
        # 添加关联信息（已通过 selectinload 预加载）
        if s.application:
            if s.application.resume:
                item["candidate_name"] = s.application.resume.candidate_name
            if s.application.position:
                item["position_title"] = s.application.position.title
        items.append(item)
    
    return paged_response(items, total, page, page_size)


@router.post("", summary="创建沉浸式面试会话", response_model=ResponseModel[ImmersiveSessionResponse])
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
    
    # 检查是否已存在会话（1:1关系）
    existing_session = await immersive_crud.get_by_application(db, data.application_id)
    if existing_session:
        # 如果已存在，可以选择删除旧会话或返回错误
        # 这里选择删除旧会话，重新开始
        await immersive_crud.delete(db, id=existing_session.id)
    
    # 创建新会话
    session = await immersive_crud.create_session(db, obj_in=data)
    
    # 手动构建响应，避免 model_validate 触发懒加载
    response = {
        "id": session.id,
        "application_id": session.application_id,
        "local_camera_enabled": session.local_camera_enabled,
        "stream_url": session.stream_url,
        "config": session.config or {},
        "is_recording": session.is_recording,
        "is_completed": session.is_completed,
        "transcripts": session.transcripts or [],
        "speaker_segments": session.speaker_segments or [],
        "state_history": session.state_history or [],
        "duration_seconds": session.duration_seconds or 0,
        "interviewer_speak_ratio": session.interviewer_speak_ratio or 0,
        "candidate_speak_ratio": session.candidate_speak_ratio or 0,
        "final_analysis": session.final_analysis,
        "candidate_name": application.resume.candidate_name if application.resume else None,
        "position_title": application.position.title if application.position else None,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }
    
    return success_response(
        data=response,
        message="沉浸式面试会话创建成功"
    )


@router.get("/{session_id}", summary="获取沉浸式面试会话详情")
async def get_immersive_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取沉浸式面试会话详情
    
    如果会话已完成，返回完整的数据汇总
    """
    session = await immersive_crud.get_with_application(db, session_id)
    if not session:
        raise NotFoundException(f"沉浸式面试会话不存在: {session_id}")
    
    # 基础响应字典
    base_response = {
        "id": session.id,
        "application_id": session.application_id,
        "local_camera_enabled": session.local_camera_enabled,
        "stream_url": session.stream_url,
        "config": session.config or {},
        "is_recording": session.is_recording,
        "is_completed": session.is_completed,
        "transcripts": session.transcripts or [],
        "speaker_segments": session.speaker_segments or [],
        "state_history": session.state_history or [],
        "duration_seconds": session.duration_seconds or 0,
        "interviewer_speak_ratio": session.interviewer_speak_ratio or 0,
        "candidate_speak_ratio": session.candidate_speak_ratio or 0,
        "final_analysis": session.final_analysis,
        "candidate_name": None,
        "position_title": None,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }
    
    # 添加关联信息（已通过 selectinload 预加载）
    if session.application:
        if session.application.resume:
            base_response["candidate_name"] = session.application.resume.candidate_name
        if session.application.position:
            base_response["position_title"] = session.application.position.title
    
    # 如果会话已完成，返回完整汇总
    if session.is_completed:
        summary_data = await immersive_crud.get_session_summary(db, session_id)
        base_response["statistics"] = summary_data["statistics"]
        base_response["psychological_summary"] = summary_data["psychological_summary"]
        base_response["full_transcripts"] = summary_data["transcripts"]
        base_response["full_speaker_segments"] = summary_data["speaker_segments"]
        base_response["full_state_history"] = summary_data["state_history"]
        
        if summary_data["candidate_info"]:
            base_response["candidate_name"] = summary_data["candidate_info"].get("name")
            base_response["position_title"] = summary_data["candidate_info"].get("position_title")
    
    return success_response(data=base_response)


@router.delete("/{session_id}", summary="删除沉浸式面试会话", response_model=MessageResponse)
async def delete_immersive_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    删除沉浸式面试会话
    """
    session = await immersive_crud.get(db, session_id)
    if not session:
        raise NotFoundException(f"沉浸式面试会话不存在: {session_id}")
    
    await immersive_crud.delete(db, id=session_id)
    return success_response(message="沉浸式面试会话删除成功")


@router.post("/{session_id}/start", summary="开始录制", response_model=DictResponse)
async def start_immersive_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    开始沉浸式面试录制
    """
    try:
        session = await immersive_crud.start_recording(db, session_id)
        
        return success_response(
            data={
                "session_id": session.id,
                "status": "recording",
                "start_time": session.start_time.isoformat() if session.start_time else None
            },
            message="面试录制已开始"
        )
    except ValueError as e:
        raise NotFoundException(str(e))
    except Exception as e:
        raise BadRequestException(f"开始录制失败: {str(e)}")


@router.post("/{session_id}/stop", summary="停止录制", response_model=DictResponse)
async def stop_immersive_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    停止沉浸式面试录制（但不完成会话）
    """
    try:
        session = await immersive_crud.stop_recording(db, session_id)
        
        return success_response(
            data={
                "session_id": session.id,
                "status": "stopped",
                "duration_seconds": session.duration_seconds,
                "end_time": session.end_time.isoformat() if session.end_time else None
            },
            message="面试录制已停止"
        )
    except ValueError as e:
        raise NotFoundException(str(e))
    except Exception as e:
        raise BadRequestException(f"停止录制失败: {str(e)}")


@router.post("/{session_id}/complete", summary="完成面试会话")
async def complete_immersive_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    完成沉浸式面试会话并返回简化的数据汇总
    
    返回内容：
    - 统计数据：发言数、发言占比、总体抑郁水平
    - 会话历史：每条记录捆绑三项心理评分（大五人格、欺骗检测、抑郁值）
    - 候选人信息
    
    数据会自动保存到 final_analysis 字段供后续推荐使用
    """
    try:
        # 完成会话
        await immersive_crud.complete_session(db, session_id)
        
        # 获取简化的完成数据（同时保存到 final_analysis）
        complete_data = await immersive_crud.get_simplified_complete_data(db, session_id)
        
        return success_response(
            data=complete_data,
            message="沉浸式面试会话已完成"
        )
    except ValueError as e:
        raise NotFoundException(str(e))
    except Exception as e:
        raise BadRequestException(f"完成会话失败: {str(e)}")


@router.post("/{session_id}/sync", summary="同步实时数据", response_model=DictResponse)
async def sync_realtime_data(
    session_id: str,
    data: SimplifiedSyncRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    同步实时数据（简化版）
    
    请求结构：
    ```json
    {
      "utterances": [
        {
          "speaker": "interviewer" | "candidate",
          "text": "发言内容",
          "timestamp": 1768720937024,  // 毫秒时间戳
          "candidate_scores": {        // 候选人心理评分（每次都带）
            "big_five": {...},
            "deception": {...},
            "depression": {...}
          }
        }
      ]
    }
    """
    try:
        session = await immersive_crud.sync_utterances(db, session_id, data)
        
        return success_response(
            data={
                "session_id": session.id,
                "synced_count": len(data.utterances),
                "total_utterances": len(session.speaker_segments) if session.speaker_segments else 0
            },
            message="实时数据同步成功"
        )
    except ValueError as e:
        raise NotFoundException(str(e))
    except Exception as e:
        raise BadRequestException(f"数据同步失败: {str(e)}")


@router.post("/{session_id}/sync-legacy", summary="同步实时数据（旧版）", response_model=DictResponse)
async def sync_realtime_data_legacy(
    session_id: str,
    data: SyncDataRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    批量同步实时数据（旧版，保留兼容）
    
    包括转录记录、说话人分段、状态记录等
    """
    try:
        session = await immersive_crud.sync_realtime_data(db, session_id, data)
        
        sync_count = {
            "transcripts": len(data.transcripts) if data.transcripts else 0,
            "speaker_segments": len(data.speaker_segments) if data.speaker_segments else 0,
            "state_records": len(data.state_records) if data.state_records else 0,
        }
        
        return success_response(
            data={
                "session_id": session.id,
                "sync_count": sync_count,
                "total_transcripts": session.transcript_count,
                "total_segments": session.segment_count,
                "total_states": len(session.state_history) if session.state_history else 0
            },
            message="实时数据同步成功"
        )
    except ValueError as e:
        raise NotFoundException(str(e))
    except Exception as e:
        raise BadRequestException(f"数据同步失败: {str(e)}")


# ========== 辅助接口（可选） ==========

@router.post("/{session_id}/transcript", summary="添加单条转录记录", response_model=DictResponse)
async def add_transcript(
    session_id: str,
    data: TranscriptCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    添加单条实时转录记录
    """
    try:
        session = await immersive_crud.add_transcript(db, session_id, data)
        
        return success_response(
            data={
                "session_id": session.id,
                "transcript_count": session.transcript_count
            },
            message="转录记录添加成功"
        )
    except ValueError as e:
        raise NotFoundException(str(e))
    except Exception as e:
        raise BadRequestException(f"添加转录记录失败: {str(e)}")


@router.post("/{session_id}/segment", summary="添加说话人分段", response_model=DictResponse)
async def add_speaker_segment(
    session_id: str,
    data: SpeakerSegmentCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    添加说话人分段（含心理分析数据）
    """
    try:
        session = await immersive_crud.add_speaker_segment(db, session_id, data)
        
        return success_response(
            data={
                "session_id": session.id,
                "segment_count": session.segment_count,
                "candidate_segments": session.candidate_segments_count
            },
            message="说话人分段添加成功"
        )
    except ValueError as e:
        raise NotFoundException(str(e))
    except Exception as e:
        raise BadRequestException(f"添加说话人分段失败: {str(e)}")


@router.post("/{session_id}/state", summary="添加状态记录", response_model=DictResponse)
async def add_state_record(
    session_id: str,
    data: StateRecordCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    添加候选人状态记录
    """
    try:
        session = await immersive_crud.add_state_record(db, session_id, data)
        
        return success_response(
            data={
                "session_id": session.id,
                "state_count": len(session.state_history) if session.state_history else 0
            },
            message="状态记录添加成功"
        )
    except ValueError as e:
        raise NotFoundException(str(e))
    except Exception as e:
        raise BadRequestException(f"添加状态记录失败: {str(e)}")


@router.get("/{session_id}/statistics", summary="获取会话统计", response_model=DictResponse)
async def get_session_statistics(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取会话统计数据
    """
    try:
        statistics = await immersive_crud.calculate_session_statistics(db, session_id)
        
        return success_response(
            data=statistics,
            message="统计数据获取成功"
        )
    except ValueError as e:
        raise NotFoundException(str(e))
    except Exception as e:
        raise BadRequestException(f"获取统计数据失败: {str(e)}")


@router.post("/{session_id}/questions", summary="生成智能问题建议", response_model=DictResponse)
async def generate_question_suggestions(
    session_id: str,
    data: GenerateQuestionsRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    基于心理状态和对话历史生成智能问题建议
    
    沉浸式面试的问题建议会考虑：
    - 候选人当前的心理状态（紧张程度、参与度等）
    - 对话历史和话题流向
    - 大五人格分析结果
    - 抑郁风险评估
    """
    try:
        suggestions = await immersive_crud.generate_question_suggestions(
            db=db,
            session_id=session_id,
            count=data.count,
            difficulty=data.difficulty,
            focus_areas=data.focus_areas,
            use_psychological_context=data.use_psychological_context,
            use_conversation_history=data.use_conversation_history,
            question_type=data.question_type
        )
        
        return success_response(
            data={
                "suggestions": suggestions,
                "total_count": len(suggestions),
                "generation_context": {
                    "difficulty": data.difficulty,
                    "question_type": data.question_type,
                    "psychological_context_used": False,
                    "conversation_history_used": data.use_conversation_history
                }
            },
            message="问题建议生成成功"
        )
    except ValueError as e:
        raise NotFoundException(str(e))
    except Exception as e:
        raise BadRequestException(f"生成问题建议失败: {str(e)}")


@router.get("/{session_id}/insights", summary="获取实时面试洞察", response_model=DictResponse)
async def get_interview_insights(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取基于心理状态的实时面试洞察和建议
    """
    try:
        session = await immersive_crud.get(db, session_id)
        if not session:
            raise NotFoundException(f"沉浸式面试会话不存在: {session_id}")
        
        insights = []
        alerts = []
        suggestions = []
        
        # 基于心理状态生成洞察
        if session.state_history:
            latest_state = session.get_latest_psychological_state()
            if latest_state:
                # 分析参与度
                engagement = latest_state.get("engagement", 0)
                if engagement > 0.8:
                    insights.append({
                        "category": "参与度",
                        "content": "候选人参与度很高，表现出强烈的兴趣",
                        "severity": "info",
                        "timestamp": datetime.now().isoformat()
                    })
                elif engagement < 0.5:
                    alerts.append({
                        "category": "参与度",
                        "content": "候选人参与度较低，建议调整话题或提问方式",
                        "severity": "warning",
                        "timestamp": datetime.now().isoformat()
                    })
                    suggestions.append("尝试询问候选人感兴趣的技术领域")
                
                # 分析紧张程度
                nervousness = latest_state.get("nervousness", 0)
                if nervousness > 0.7:
                    alerts.append({
                        "category": "情绪状态",
                        "content": "候选人紧张程度较高，建议营造轻松氛围",
                        "severity": "warning",
                        "timestamp": datetime.now().isoformat()
                    })
                    suggestions.append("可以先聊一些轻松的话题，让候选人放松")
                
                # 分析自信程度
                confidence = latest_state.get("confidence_level", 0)
                if confidence > 0.8:
                    insights.append({
                        "category": "自信程度",
                        "content": "候选人表现出很强的自信心",
                        "severity": "info",
                        "timestamp": datetime.now().isoformat()
                    })
        
        # 分析说话比例
        if session.candidate_speak_ratio > 0.7:
            insights.append({
                "category": "对话平衡",
                "content": "候选人表达欲望强烈，善于沟通",
                "severity": "info",
                "timestamp": datetime.now().isoformat()
            })
        elif session.candidate_speak_ratio < 0.3:
            alerts.append({
                "category": "对话平衡",
                "content": "候选人说话较少，建议引导其多表达",
                "severity": "warning",
                "timestamp": datetime.now().isoformat()
            })
            suggestions.append("尝试问一些开放性问题，鼓励候选人多分享")
        
        return success_response(
            data={
                "insights": insights,
                "alerts": alerts,
                "suggestions": suggestions,
                "session_quality_score": session.session_quality_score,
                "psychological_wellness_score": session.psychological_wellness_score
            },
            message="面试洞察获取成功"
        )
    except ValueError as e:
        raise NotFoundException(str(e))
    except Exception as e:
        raise BadRequestException(f"获取面试洞察失败: {str(e)}")