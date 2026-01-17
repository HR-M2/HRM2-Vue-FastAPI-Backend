"""
沉浸式面试 API 路由

提供双摄像头面试、说话人识别、实时状态分析等功能
"""
from typing import Optional
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
    SyncDataRequest,
    TranscriptCreate,
    SpeakerSegmentCreate,
    StateRecordCreate,
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
        item = ImmersiveSessionResponse.model_validate(s)
        # 添加关联信息
        if s.application:
            if s.application.resume:
                item.candidate_name = s.application.resume.candidate_name
            if s.application.position:
                item.position_title = s.application.position.title
        items.append(item.model_dump())
    
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
    
    # 构建响应
    response = ImmersiveSessionResponse.model_validate(session)
    if application.resume:
        response.candidate_name = application.resume.candidate_name
    if application.position:
        response.position_title = application.position.title
    
    return success_response(
        data=response.model_dump(),
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
    
    # 如果会话已完成，返回完整汇总
    if session.is_completed:
        # 获取完整汇总数据
        summary_data = await immersive_crud.get_session_summary(db, session_id)
        
        # 构建详细响应
        response = ImmersiveSessionDetailResponse.model_validate(session)
        response.statistics = summary_data["statistics"]
        response.psychological_summary = summary_data["psychological_summary"]
        response.full_transcripts = summary_data["transcripts"]
        response.full_speaker_segments = summary_data["speaker_segments"]
        response.full_state_history = summary_data["state_history"]
        
        # 添加关联信息
        if summary_data["candidate_info"]:
            response.candidate_name = summary_data["candidate_info"].get("name")
            response.position_title = summary_data["candidate_info"].get("position_title")
        
        return success_response(data=response.model_dump())
    else:
        # 会话未完成，返回基础信息
        response = ImmersiveSessionResponse.model_validate(session)
        if session.application:
            if session.application.resume:
                response.candidate_name = session.application.resume.candidate_name
            if session.application.position:
                response.position_title = session.application.position.title
        
        return success_response(data=response.model_dump())


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
    完成沉浸式面试会话并返回完整数据汇总
    
    包括所有转录记录、心理分析数据、统计信息等
    """
    try:
        # 完成会话
        session = await immersive_crud.complete_session(db, session_id)
        
        # 获取完整汇总数据
        summary_data = await immersive_crud.get_session_summary(db, session_id)
        
        # 构建详细响应
        response = ImmersiveSessionDetailResponse.model_validate(session)
        response.statistics = summary_data["statistics"]
        response.psychological_summary = summary_data["psychological_summary"]
        response.full_transcripts = summary_data["transcripts"]
        response.full_speaker_segments = summary_data["speaker_segments"]
        response.full_state_history = summary_data["state_history"]
        
        # 添加关联信息
        if summary_data["candidate_info"]:
            response.candidate_name = summary_data["candidate_info"].get("name")
            response.position_title = summary_data["candidate_info"].get("position_title")
        
        return success_response(
            data=response.model_dump(),
            message="沉浸式面试会话已完成"
        )
    except ValueError as e:
        raise NotFoundException(str(e))
    except Exception as e:
        raise BadRequestException(f"完成会话失败: {str(e)}")


@router.post("/{session_id}/sync", summary="同步实时数据", response_model=DictResponse)
async def sync_realtime_data(
    session_id: str,
    data: SyncDataRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    批量同步实时数据
    
    包括转录记录、说话人分段、状态记录等
    """
    try:
        session = await immersive_crud.sync_realtime_data(db, session_id, data)
        
        # 统计同步的数据量
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