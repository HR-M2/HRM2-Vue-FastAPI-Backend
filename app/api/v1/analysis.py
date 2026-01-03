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
from app.core.exceptions import NotFoundException, BadRequestException
from app.crud import analysis_crud, application_crud, screening_crud, interview_crud
from app.models import (
    RecommendationLevel,
    ComprehensiveAnalysisCreate,
    ComprehensiveAnalysisResponse,
    ComprehensiveAnalysisUpdate,
)
from app.services.agents import AnalysisService, get_llm_client

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
    为指定应聘申请创建综合分析（支持重新分析）
    
    调用 AI Agent 进行多维度评估，生成最终录用建议。
    如果已有分析记录，会更新该记录。
    """
    if not get_llm_client().is_configured():
        raise BadRequestException("LLM服务未配置，请检查API Key")
    
    # 验证应聘申请存在
    application = await application_crud.get_detail(db, data.application_id)
    if not application:
        raise NotFoundException(f"应聘申请不存在: {data.application_id}")
    
    # 检查是否已有分析记录（用于重新分析）
    existing_analysis = await analysis_crud.get_by_application(db, data.application_id)
    
    # 收集分析所需数据
    resume_content = ""
    candidate_name = "候选人"
    job_config = {}
    
    if application.resume:
        resume_content = application.resume.content or ""
        candidate_name = application.resume.candidate_name
    
    if application.position:
        job_config = {"title": application.position.title}
    
    # 获取筛选报告
    screening_report = {}
    screening_task = await screening_crud.get_by_application(db, data.application_id)
    if screening_task:
        screening_report = {
            "comprehensive_score": screening_task.score,
            "summary": screening_task.summary,
        }
    
    # 获取面试记录
    interview_records = []
    interview_report = {}
    interview_session = await interview_crud.get_by_application(db, data.application_id)
    if interview_session:
        interview_records = interview_session.messages or []
        interview_report = interview_session.report or {}
    
    # 执行 AI 综合分析
    analyzer = AnalysisService(job_config)
    ai_result = await analyzer.analyze(
        candidate_name=candidate_name,
        resume_content=resume_content,
        screening_report=screening_report,
        interview_records=interview_records,
        interview_report=interview_report,
    )
    
    # 映射 AI 结果到数据库字段
    recommendation = ai_result.get("recommendation", {})
    # 使用中文标签而不是英文标识符
    recommendation_level = recommendation.get("label", "推荐录用")
    
    # 保留完整维度评分数据（包含优势、不足等详情）
    dimension_scores = ai_result.get("dimension_scores", {})
    
    analysis_result = {
        "final_score": ai_result.get("final_score", 60.0),
        "recommendation_level": recommendation_level,
        "recommendation_reason": recommendation.get("label", ""),
        "suggested_action": recommendation.get("action", ""),
        "dimension_scores": dimension_scores,
        "report": ai_result.get("comprehensive_report", ""),
        "input_snapshot": {
            "position": application.position.title if application.position else None,
            "candidate": candidate_name,
        }
    }
    
    # 根据是否已有记录决定创建或更新
    if existing_analysis:
        # 更新已有分析记录
        update_data = ComprehensiveAnalysisUpdate(**analysis_result)
        analysis = await analysis_crud.update_analysis(
            db, db_obj=existing_analysis, obj_in=update_data
        )
        message = "综合分析已更新"
    else:
        # 创建新分析记录
        analysis = await analysis_crud.create_analysis(
            db, obj_in=data, analysis_result=analysis_result
        )
        message = "综合分析创建成功"
    
    response = ComprehensiveAnalysisResponse.model_validate(analysis)
    if application.resume:
        response.candidate_name = application.resume.candidate_name
    if application.position:
        response.position_title = application.position.title
    
    return success_response(
        data=response.model_dump(),
        message=message
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
