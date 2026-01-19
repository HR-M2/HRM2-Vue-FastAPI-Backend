"""
心理分析报告 API 模块
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundException, BadRequestException
from app.core.response import success_response
from app.crud.psychological import psychological_crud
from app.crud.immersive import immersive_crud
from app.schemas.psychological import (
    PsychologicalReportResponse,
    PsychologicalReportGenerate,
)
from app.services.agents.psychological_agent import PsychologicalAnalysisAgent

router = APIRouter(prefix="/psychological", tags=["心理分析"])


@router.post("/{session_id}/generate", summary="生成心理分析报告")
async def generate_psychological_report(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    生成心理分析报告
    
    基于沉浸式面试会话的数据，调用 AI Agent 生成心理分析报告。
    
    **注意**：
    - 面试会话必须已完成
    - 如果已存在报告，会覆盖更新
    - 生成过程约需 10-30 秒
    
    **数据来源**：
    - 面试记录中的大五人格评分
    - 面试记录中的欺骗检测评分
    - 面试记录中的抑郁风险评分
    - 发言模式统计
    """
    # 获取面试数据
    interview_data = await psychological_crud.get_interview_data(db, session_id)
    if not interview_data:
        raise NotFoundException(f"未找到已完成的面试会话: {session_id}")
    
    # 检查会话记录是否有心理数据
    conversation_history = interview_data.get("conversation_history", [])
    if not conversation_history:
        raise BadRequestException("面试会话无对话记录，无法生成心理分析报告")
    
    # 调用 AI Agent 生成分析
    agent = PsychologicalAnalysisAgent()
    try:
        analysis_result = await agent.analyze(interview_data)
    except Exception as e:
        raise BadRequestException(f"心理分析生成失败: {str(e)}")
    
    # 保存报告（创建或更新）
    report_data = {
        "big_five_scores": analysis_result.big_five_analysis.scores.model_dump(),
        "big_five_analysis": analysis_result.big_five_analysis.model_dump(),
        "deception_score": analysis_result.deception_analysis.overall_score,
        "deception_analysis": analysis_result.deception_analysis.model_dump(),
        "depression_score": analysis_result.depression_analysis.average_score,
        "depression_level": analysis_result.depression_analysis.risk_level,
        "depression_analysis": analysis_result.depression_analysis.model_dump(),
        "speech_pattern_analysis": analysis_result.speech_pattern_analysis.model_dump(),
        "overall_score": analysis_result.overall_score,
        "risk_level": analysis_result.risk_level,
        "overall_summary": analysis_result.overall_summary,
        "recommendations": analysis_result.recommendations,
        "report_markdown": analysis_result.report_markdown,
        "input_snapshot": interview_data,
    }
    
    report = await psychological_crud.create_or_update(
        db,
        session_id=session_id,
        application_id=interview_data["application_id"],
        report_data=report_data
    )
    
    # 构建响应
    response = {
        "id": report.id,
        "session_id": report.session_id,
        "application_id": report.application_id,
        "big_five_scores": report.big_five_scores,
        "big_five_analysis": report.big_five_analysis,
        "deception_score": report.deception_score,
        "deception_analysis": report.deception_analysis,
        "depression_score": report.depression_score,
        "depression_level": report.depression_level,
        "depression_analysis": report.depression_analysis,
        "speech_pattern_analysis": report.speech_pattern_analysis,
        "overall_score": report.overall_score,
        "risk_level": report.risk_level,
        "overall_summary": report.overall_summary,
        "recommendations": report.recommendations,
        "report_markdown": report.report_markdown,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
    }
    
    return success_response(data=response, message="心理分析报告生成成功")


@router.get("/{session_id}", summary="获取心理分析报告")
async def get_psychological_report(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取心理分析报告
    
    根据面试会话ID获取已生成的心理分析报告。
    如果报告不存在，返回 404。
    """
    report = await psychological_crud.get_by_session(db, session_id)
    if not report:
        raise NotFoundException(f"未找到该面试会话的心理分析报告: {session_id}")
    
    response = {
        "id": report.id,
        "session_id": report.session_id,
        "application_id": report.application_id,
        "big_five_scores": report.big_five_scores,
        "big_five_analysis": report.big_five_analysis,
        "deception_score": report.deception_score,
        "deception_analysis": report.deception_analysis,
        "depression_score": report.depression_score,
        "depression_level": report.depression_level,
        "depression_analysis": report.depression_analysis,
        "speech_pattern_analysis": report.speech_pattern_analysis,
        "overall_score": report.overall_score,
        "risk_level": report.risk_level,
        "overall_summary": report.overall_summary,
        "recommendations": report.recommendations,
        "report_markdown": report.report_markdown,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
    }
    
    return success_response(data=response)


@router.get("/by-application/{application_id}", summary="按申请ID获取心理分析报告")
async def get_psychological_report_by_application(
    application_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    按申请ID获取心理分析报告
    
    获取该应聘申请关联的最新心理分析报告。
    """
    report = await psychological_crud.get_by_application(db, application_id)
    if not report:
        raise NotFoundException(f"未找到该申请的心理分析报告: {application_id}")
    
    response = {
        "id": report.id,
        "session_id": report.session_id,
        "application_id": report.application_id,
        "big_five_scores": report.big_five_scores,
        "big_five_analysis": report.big_five_analysis,
        "deception_score": report.deception_score,
        "deception_analysis": report.deception_analysis,
        "depression_score": report.depression_score,
        "depression_level": report.depression_level,
        "depression_analysis": report.depression_analysis,
        "speech_pattern_analysis": report.speech_pattern_analysis,
        "overall_score": report.overall_score,
        "risk_level": report.risk_level,
        "overall_summary": report.overall_summary,
        "recommendations": report.recommendations,
        "report_markdown": report.report_markdown,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
    }
    
    return success_response(data=response)


@router.delete("/{session_id}", summary="删除心理分析报告")
async def delete_psychological_report(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    删除心理分析报告
    """
    deleted = await psychological_crud.delete_by_session(db, session_id)
    if not deleted:
        raise NotFoundException(f"未找到该面试会话的心理分析报告: {session_id}")
    
    return success_response(message="心理分析报告已删除")


@router.get("/{session_id}/exists", summary="检查心理分析报告是否存在")
async def check_psychological_report_exists(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    检查心理分析报告是否存在
    
    用于前端判断是否需要显示"生成报告"按钮
    """
    report = await psychological_crud.get_by_session(db, session_id)
    
    return success_response(data={
        "exists": report is not None,
        "report_id": report.id if report else None,
        "created_at": report.created_at if report else None,
    })
