"""
简历筛选 API 路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from urllib.parse import quote

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
from app.crud import screening_crud, application_crud
from app.models import (
    TaskStatus,
    ScreeningTaskCreate,
    ScreeningTaskResponse,
    ScreeningResultUpdate,
)

router = APIRouter()


@router.get("", summary="获取筛选任务列表", response_model=PagedResponseModel[ScreeningTaskResponse])
async def get_screening_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    application_id: Optional[str] = Query(None, description="应聘申请ID"),
    status: Optional[str] = Query(None, description="状态筛选"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取筛选任务列表（包含候选人和岗位信息）
    """
    skip = (page - 1) * page_size
    
    if application_id:
        # 1:1 关系，直接获取单个任务
        task = await screening_crud.get_by_application(db, application_id)
        tasks = [task] if task else []
    elif status:
        tasks = await screening_crud.get_list_with_details(
            db, status=status, skip=skip, limit=page_size
        )
    else:
        tasks = await screening_crud.get_list_with_details(
            db, skip=skip, limit=page_size
        )
    
    total = await screening_crud.count(db)
    
    items = []
    for t in tasks:
        response = ScreeningTaskResponse.model_validate(t)
        # 填充关联信息
        if hasattr(t, 'application') and t.application:
            if t.application.resume:
                response.candidate_name = t.application.resume.candidate_name
            if t.application.position:
                response.position_title = t.application.position.title
        items.append(response.model_dump())
    
    return paged_response(items, total, page, page_size)


@router.post("", summary="创建筛选任务", response_model=ResponseModel[ScreeningTaskResponse])
async def create_screening_task(
    data: ScreeningTaskCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    为指定应聘申请创建筛选任务
    """
    # 验证应聘申请存在
    application = await application_crud.get_with_relations(db, data.application_id)
    if not application:
        raise NotFoundException(f"应聘申请不存在: {data.application_id}")
    
    task = await screening_crud.create(db, obj_in=data)
    
    response = ScreeningTaskResponse.model_validate(task)
    if application.resume:
        response.candidate_name = application.resume.candidate_name
    if application.position:
        response.position_title = application.position.title
    
    return success_response(
        data=response.model_dump(),
        message="筛选任务创建成功"
    )


@router.get("/{task_id}", summary="获取筛选任务详情", response_model=ResponseModel[ScreeningTaskResponse])
async def get_screening_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取筛选任务详情
    
    如果任务引用了历史经验，会返回经验的详细内容，
    便于用户了解 AI 的决策依据。
    """
    task = await screening_crud.get_with_application(db, task_id)
    if not task:
        raise NotFoundException(f"筛选任务不存在: {task_id}")
    
    response = ScreeningTaskResponse.model_validate(task)
    if task.application:
        if task.application.resume:
            response.candidate_name = task.application.resume.candidate_name
            response.resume_content = task.application.resume.content
        if task.application.position:
            response.position_title = task.application.position.title
    
    # 如果有引用的经验 ID，获取经验详情
    if task.applied_experience_ids:
        from app.crud import experience_crud
        from app.models import AgentExperienceResponse
        experiences = await experience_crud.get_by_ids(db, task.applied_experience_ids)
        response.applied_experiences = [
            {
                "id": exp.id,
                "learned_rule": exp.learned_rule,
                "source_feedback": exp.source_feedback,
                "category": exp.category,
            }
            for exp in experiences
        ]
    
    return success_response(data=response.model_dump())


@router.get("/{task_id}/status", summary="获取筛选任务状态", response_model=DictResponse)
async def get_screening_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取筛选任务状态（轮询用）
    进度从内存缓存读取，其他信息从数据库读取
    """
    from app.core.progress_cache import progress_cache
    
    task = await screening_crud.get(db, task_id)
    if not task:
        raise NotFoundException(f"筛选任务不存在: {task_id}")
    
    # 从缓存获取实时进度
    cached = progress_cache.get(task_id)
    progress = cached.progress if cached else (100 if task.status == "completed" else 0)
    current_speaker = cached.current_speaker if cached else ""
    
    return success_response(data={
        "id": task.id,
        "status": task.status,
        "progress": progress,
        "current_speaker": current_speaker,
        "error_message": task.error_message,
        "score": task.score,
        "dimension_scores": task.dimension_scores,
        "summary": task.summary,
        "recommendation": task.recommendation,
    })


@router.patch("/{task_id}", summary="更新筛选结果", response_model=ResponseModel[ScreeningTaskResponse])
async def update_screening_result(
    task_id: str,
    data: ScreeningResultUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    更新筛选任务结果（供 AI 服务回调）
    """
    task = await screening_crud.get(db, task_id)
    if not task:
        raise NotFoundException(f"筛选任务不存在: {task_id}")
    
    task = await screening_crud.update(db, db_obj=task, obj_in=data)
    
    return success_response(
        data=ScreeningTaskResponse.model_validate(task).model_dump(),
        message="筛选结果更新成功"
    )


@router.delete("/{task_id}", summary="删除筛选任务", response_model=MessageResponse)
async def delete_screening_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    删除筛选任务
    """
    task = await screening_crud.get(db, task_id)
    if not task:
        raise NotFoundException(f"筛选任务不存在: {task_id}")
    
    await screening_crud.delete(db, id=task_id)
    return success_response(message="筛选任务删除成功")


@router.get("/{task_id}/download", summary="下载筛选报告")
async def download_screening_report(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    下载筛选报告（Markdown 格式）
    """
    task = await screening_crud.get_with_application(db, task_id)
    if not task:
        raise NotFoundException(f"筛选任务不存在: {task_id}")
    
    if not task.report_content:
        raise NotFoundException("该任务暂无报告内容")
    
    # 构建文件名
    candidate_name = "候选人"
    if task.application and task.application.resume:
        candidate_name = task.application.resume.candidate_name or "候选人"
    filename = f"{candidate_name}_筛选报告.md"
    
    # 返回文件响应
    return Response(
        content=task.report_content.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        }
    )
