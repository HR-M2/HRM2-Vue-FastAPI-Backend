"""
应聘申请 API 路由
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
from app.core.exceptions import NotFoundException, ConflictException, BadRequestException
from app.crud import application_crud, position_crud, resume_crud
from app.models.application import ApplicationStatus
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
    ApplicationListResponse,
    ApplicationDetailResponse,
    ScreeningTaskBrief,
    VideoAnalysisBrief,
    InterviewSessionBrief,
    ComprehensiveAnalysisBrief,
)

router = APIRouter()


@router.get("", summary="获取应聘申请列表", response_model=PagedResponseModel[ApplicationListResponse])
async def get_applications(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    position_id: Optional[str] = Query(None, description="岗位ID筛选"),
    resume_id: Optional[str] = Query(None, description="简历ID筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取应聘申请列表，支持多条件筛选
    """
    skip = (page - 1) * page_size
    
    if position_id:
        applications = await application_crud.get_by_position(
            db, position_id, skip=skip, limit=page_size
        )
        total = await application_crud.count_by_position(db, position_id)
    elif resume_id:
        applications = await application_crud.get_by_resume(
            db, resume_id, skip=skip, limit=page_size
        )
        total = len(applications)
    elif status:
        applications = await application_crud.get_by_status(
            db, status, skip=skip, limit=page_size
        )
        total = await application_crud.count_by_status(db, status)
    else:
        applications = await application_crud.get_multi(
            db, skip=skip, limit=page_size
        )
        total = await application_crud.count(db)
    
    items = []
    for app in applications:
        item = ApplicationListResponse.model_validate(app)
        if app.position:
            item.position_title = app.position.title
        if app.resume:
            item.candidate_name = app.resume.candidate_name
        items.append(item.model_dump())
    
    return paged_response(items, total, page, page_size)


@router.post("", summary="创建应聘申请", response_model=ResponseModel[ApplicationResponse])
async def create_application(
    data: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    创建新的应聘申请（简历投递岗位）
    """
    # 验证岗位存在
    position = await position_crud.get(db, data.position_id)
    if not position:
        raise NotFoundException(f"岗位不存在: {data.position_id}")
    
    # 验证简历存在
    resume = await resume_crud.get(db, data.resume_id)
    if not resume:
        raise NotFoundException(f"简历不存在: {data.resume_id}")
    
    # 检查是否已存在相同申请
    if await application_crud.exists(db, data.position_id, data.resume_id):
        raise ConflictException("该简历已投递此岗位")
    
    application = await application_crud.create_application(db, obj_in=data)
    
    response = ApplicationResponse.model_validate(application)
    response.position_title = position.title
    response.candidate_name = resume.candidate_name
    
    return success_response(
        data=response.model_dump(),
        message="应聘申请创建成功"
    )


@router.get("/{application_id}", summary="获取应聘申请详情", response_model=ResponseModel[ApplicationDetailResponse])
async def get_application(
    application_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取应聘申请详情（含所有关联数据）
    """
    application = await application_crud.get_detail(db, application_id)
    if not application:
        raise NotFoundException(f"应聘申请不存在: {application_id}")
    
    # 构建详细响应
    response = ApplicationDetailResponse.model_validate(application)
    
    if application.position:
        response.position_title = application.position.title
    if application.resume:
        response.candidate_name = application.resume.candidate_name
    
    # 添加关联数据简要信息
    response.screening_tasks = [
        ScreeningTaskBrief(
            id=t.id,
            status=t.status,
            score=t.score,
            recommendation=t.recommendation,
            created_at=t.created_at
        ) for t in application.screening_tasks
    ]
    
    response.video_analyses = [
        VideoAnalysisBrief(
            id=v.id,
            video_name=v.video_name,
            status=v.status,
            created_at=v.created_at
        ) for v in application.video_analyses
    ]
    
    response.interview_sessions = [
        InterviewSessionBrief(
            id=i.id,
            interview_type=i.interview_type,
            is_completed=i.is_completed,
            final_score=i.final_score,
            current_round=i.current_round,
            created_at=i.created_at
        ) for i in application.interview_sessions
    ]
    
    response.comprehensive_analyses = [
        ComprehensiveAnalysisBrief(
            id=a.id,
            final_score=a.final_score,
            recommendation_level=a.recommendation_level,
            created_at=a.created_at
        ) for a in application.comprehensive_analyses
    ]
    
    return success_response(data=response.model_dump())


@router.patch("/{application_id}", summary="更新应聘申请", response_model=ResponseModel[ApplicationResponse])
async def update_application(
    application_id: str,
    data: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    更新应聘申请状态
    """
    application = await application_crud.get(db, application_id)
    if not application:
        raise NotFoundException(f"应聘申请不存在: {application_id}")
    
    # 验证状态值
    if data.status:
        valid_statuses = [s.value for s in ApplicationStatus]
        if data.status not in valid_statuses:
            raise BadRequestException(f"无效的状态值: {data.status}")
    
    application = await application_crud.update_application(
        db, db_obj=application, obj_in=data
    )
    
    return success_response(
        data=ApplicationResponse.model_validate(application).model_dump(),
        message="应聘申请更新成功"
    )


@router.delete("/{application_id}", summary="删除应聘申请", response_model=MessageResponse)
async def delete_application(
    application_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    删除应聘申请（同时删除关联的筛选/分析数据）
    """
    application = await application_crud.get(db, application_id)
    if not application:
        raise NotFoundException(f"应聘申请不存在: {application_id}")
    
    await application_crud.delete(db, id=application_id)
    return success_response(message="应聘申请删除成功")


@router.get("/stats/overview", summary="获取申请统计概览", response_model=DictResponse)
async def get_stats_overview(
    db: AsyncSession = Depends(get_db),
):
    """
    获取申请状态统计概览
    """
    stats = {}
    for status in ApplicationStatus:
        count = await application_crud.count_by_status(db, status.value)
        stats[status.value] = count
    
    stats["total"] = await application_crud.count(db)
    
    return success_response(data=stats)
