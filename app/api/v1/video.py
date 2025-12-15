"""
视频分析 API 路由
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
from app.core.exceptions import NotFoundException
from app.crud import video_crud, application_crud
from app.schemas.video import (
    VideoAnalysisCreate,
    VideoAnalysisResponse,
    VideoResultUpdate,
    BigFiveScores,
)

router = APIRouter()


@router.get("", summary="获取视频分析列表", response_model=PagedResponseModel[VideoAnalysisResponse])
async def get_video_analyses(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    application_id: Optional[str] = Query(None, description="应聘申请ID"),
    status: Optional[str] = Query(None, description="状态筛选"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取视频分析列表
    """
    skip = (page - 1) * page_size
    
    if application_id:
        videos = await video_crud.get_by_application(
            db, application_id, skip=skip, limit=page_size
        )
    elif status:
        videos = await video_crud.get_by_status(
            db, status, skip=skip, limit=page_size
        )
    else:
        videos = await video_crud.get_multi(db, skip=skip, limit=page_size)
    
    total = await video_crud.count(db)
    
    items = [
        VideoAnalysisResponse.model_validate(v).model_dump()
        for v in videos
    ]
    
    return paged_response(items, total, page, page_size)


@router.post("", summary="创建视频分析", response_model=ResponseModel[VideoAnalysisResponse])
async def create_video_analysis(
    data: VideoAnalysisCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    创建视频分析任务
    """
    # 验证应聘申请存在
    application = await application_crud.get_detail(db, data.application_id)
    if not application:
        raise NotFoundException(f"应聘申请不存在: {data.application_id}")
    
    video = await video_crud.create_video(db, obj_in=data)
    
    response = VideoAnalysisResponse.model_validate(video)
    if application.resume:
        response.candidate_name = application.resume.candidate_name
    if application.position:
        response.position_title = application.position.title
    
    return success_response(
        data=response.model_dump(),
        message="视频分析任务创建成功"
    )


@router.get("/{video_id}", summary="获取视频分析详情", response_model=ResponseModel[VideoAnalysisResponse])
async def get_video_analysis(
    video_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取视频分析详情
    """
    video = await video_crud.get_with_application(db, video_id)
    if not video:
        raise NotFoundException(f"视频分析不存在: {video_id}")
    
    response = VideoAnalysisResponse.model_validate(video)
    response.big_five_scores = BigFiveScores(
        openness=video.openness,
        conscientiousness=video.conscientiousness,
        extraversion=video.extraversion,
        agreeableness=video.agreeableness,
        neuroticism=video.neuroticism,
    )
    
    if video.application:
        if video.application.resume:
            response.candidate_name = video.application.resume.candidate_name
        if video.application.position:
            response.position_title = video.application.position.title
    
    return success_response(data=response.model_dump())


@router.get("/{video_id}/status", summary="获取视频分析状态", response_model=DictResponse)
async def get_video_status(
    video_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取视频分析状态（轮询用）
    """
    video = await video_crud.get(db, video_id)
    if not video:
        raise NotFoundException(f"视频分析不存在: {video_id}")
    
    return success_response(data={
        "id": video.id,
        "status": video.status,
        "error_message": video.error_message,
    })


@router.patch("/{video_id}", summary="更新视频分析结果", response_model=ResponseModel[VideoAnalysisResponse])
async def update_video_result(
    video_id: str,
    data: VideoResultUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    更新视频分析结果（供外部分析服务回调）
    """
    video = await video_crud.get(db, video_id)
    if not video:
        raise NotFoundException(f"视频分析不存在: {video_id}")
    
    video = await video_crud.update_result(db, db_obj=video, obj_in=data)
    
    return success_response(
        data=VideoAnalysisResponse.model_validate(video).model_dump(),
        message="视频分析结果更新成功"
    )


@router.delete("/{video_id}", summary="删除视频分析", response_model=MessageResponse)
async def delete_video_analysis(
    video_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    删除视频分析
    """
    video = await video_crud.get(db, video_id)
    if not video:
        raise NotFoundException(f"视频分析不存在: {video_id}")
    
    await video_crud.delete(db, id=video_id)
    return success_response(message="视频分析删除成功")
