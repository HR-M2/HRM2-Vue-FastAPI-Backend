"""
综合分析 API 路由
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
from app.crud import analysis_crud, application_crud
from app.models.analysis import RecommendationLevel
from app.schemas.analysis import (
    ComprehensiveAnalysisCreate,
    ComprehensiveAnalysisResponse,
    ComprehensiveAnalysisUpdate,
)

router = APIRouter()


@router.get("", summary="获取综合分析列表", response_model=PagedResponseModel[ComprehensiveAnalysisResponse])
async def get_analyses(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    application_id: Optional[str] = Query(None, description="应聘申请ID"),
    recommendation_level: Optional[str] = Query(None, description="推荐等级筛选"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取综合分析列表
    """
    skip = (page - 1) * page_size
    
    if application_id:
        # 1:1 关系，直接获取单个分析
        analysis = await analysis_crud.get_by_application(db, application_id)
        analyses = [analysis] if analysis else []
    elif recommendation_level:
        analyses = await analysis_crud.get_by_recommendation(
            db, recommendation_level, skip=skip, limit=page_size
        )
    else:
        analyses = await analysis_crud.get_multi(db, skip=skip, limit=page_size)
    
    total = await analysis_crud.count(db)
    
    items = [
        ComprehensiveAnalysisResponse.model_validate(a).model_dump()
        for a in analyses
    ]
    
    return paged_response(items, total, page, page_size)


@router.post("", summary="创建综合分析", response_model=ResponseModel[ComprehensiveAnalysisResponse])
async def create_analysis(
    data: ComprehensiveAnalysisCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    为指定应聘申请创建综合分析
    
    注意: 实际分析逻辑需要在 services 层实现
    """
    # 验证应聘申请存在
    application = await application_crud.get_detail(db, data.application_id)
    if not application:
        raise NotFoundException(f"应聘申请不存在: {data.application_id}")
    
    # TODO: 调用 AI 服务进行综合分析
    # 这里使用占位数据
    analysis_result = {
        "final_score": 75.0,
        "recommendation_level": RecommendationLevel.RECOMMENDED.value,
        "recommendation_reason": "综合表现良好",
        "suggested_action": "建议进入下一轮面试",
        "dimension_scores": {
            "技能匹配": 80,
            "经验匹配": 70,
            "面试表现": 75,
        },
        "report": "# 综合分析报告\n\n待 AI 服务生成...",
        "input_snapshot": {
            "position": application.position.title if application.position else None,
            "candidate": application.resume.candidate_name if application.resume else None,
        }
    }
    
    analysis = await analysis_crud.create_analysis(
        db, obj_in=data, analysis_result=analysis_result
    )
    
    response = ComprehensiveAnalysisResponse.model_validate(analysis)
    if application.resume:
        response.candidate_name = application.resume.candidate_name
    if application.position:
        response.position_title = application.position.title
    
    return success_response(
        data=response.model_dump(),
        message="综合分析创建成功"
    )


@router.get("/{analysis_id}", summary="获取综合分析详情", response_model=ResponseModel[ComprehensiveAnalysisResponse])
async def get_analysis(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取综合分析详情
    """
    analysis = await analysis_crud.get_with_application(db, analysis_id)
    if not analysis:
        raise NotFoundException(f"综合分析不存在: {analysis_id}")
    
    response = ComprehensiveAnalysisResponse.model_validate(analysis)
    if analysis.application:
        if analysis.application.resume:
            response.candidate_name = analysis.application.resume.candidate_name
        if analysis.application.position:
            response.position_title = analysis.application.position.title
    
    return success_response(data=response.model_dump())


@router.delete("/{analysis_id}", summary="删除综合分析", response_model=MessageResponse)
async def delete_analysis(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    删除综合分析
    """
    analysis = await analysis_crud.get(db, analysis_id)
    if not analysis:
        raise NotFoundException(f"综合分析不存在: {analysis_id}")
    
    await analysis_crud.delete(db, id=analysis_id)
    return success_response(message="综合分析删除成功")


@router.get("/stats/recommendation", summary="获取推荐等级统计", response_model=DictResponse)
async def get_recommendation_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    获取各推荐等级的数量统计
    """
    stats = {}
    for level in RecommendationLevel:
        analyses = await analysis_crud.get_by_recommendation(
            db, level.value, skip=0, limit=1
        )
        # 简化处理，实际应该单独实现 count 方法
        all_analyses = await analysis_crud.get_by_recommendation(
            db, level.value, skip=0, limit=10000
        )
        stats[level.value] = len(all_analyses)
    
    stats["total"] = await analysis_crud.count(db)
    
    return success_response(data=stats)
