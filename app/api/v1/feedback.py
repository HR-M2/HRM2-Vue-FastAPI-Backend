# -*- coding: utf-8 -*-
"""
Agent 反馈 API 路由

提供 HR 反馈接口，用于：
1. 接收 HR 对报告的指导性反馈
2. 将反馈转化为经验存储
3. 重新生成报告
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db
from app.core.response import success_response, ResponseModel
from app.core.exceptions import NotFoundException, BadRequestException
from app.crud import screening_crud, interview_crud, analysis_crud
from app.models import FeedbackRequest, FeedbackResponse, ExperienceCategory
from app.agents import get_experience_manager, get_llm_client

router = APIRouter()


@router.post("", summary="提交反馈并重生成报告", response_model=ResponseModel[FeedbackResponse])
async def submit_feedback(
    data: FeedbackRequest,
    regenerate: bool = Query(True, description="是否重新生成报告"),
    db: AsyncSession = Depends(get_db),
):
    """
    提交 HR 反馈，触发经验学习和报告重生成
    """
    if not get_llm_client().is_configured():
        raise BadRequestException("LLM服务未配置，请检查API Key")
    
    if data.category not in [e.value for e in ExperienceCategory]:
        raise BadRequestException(f"无效的类别: {data.category}")
    
    context = await _get_context(db, data.category, data.target_id)
    
    experience_manager = get_experience_manager()
    experience = await experience_manager.learn(
        db=db,
        category=data.category,
        feedback=data.feedback,
        context=context,
    )
    
    logger.info("经验学习完成: category={}, target_id={}, experience_id={}",
        data.category, data.target_id, experience.id)
    
    new_report = None
    if regenerate:
        new_report = await _regenerate_report(
            db=db, category=data.category, target_id=data.target_id,
            experience_manager=experience_manager,
        )
    
    return success_response(
        data=FeedbackResponse(
            learned_rule=experience.learned_rule,
            new_report=new_report,
            experience_id=experience.id,
        ).model_dump(),
        message="反馈已记录，报告已重新生成" if new_report else "反馈已记录，经验已学习"
    )


@router.get("/experiences", summary="获取经验列表")
async def get_experiences(
    category: Optional[str] = Query(None, description="按类别筛选"),
    db: AsyncSession = Depends(get_db),
):
    """获取已学习的经验列表"""
    from app.crud import experience_crud
    from app.models import AgentExperienceResponse
    
    if category:
        experiences = await experience_crud.get_by_category(db, category, limit=50)
    else:
        experiences = await experience_crud.get_multi(db, limit=50)
    
    items = [AgentExperienceResponse.model_validate(exp).model_dump() for exp in experiences]
    return success_response(data={"items": items, "total": len(items)})


@router.delete("/experiences/{experience_id}", summary="删除单条经验")
async def delete_experience(
    experience_id: str,
    db: AsyncSession = Depends(get_db),
):
    """删除指定的经验记录"""
    from app.crud import experience_crud
    
    experience = await experience_crud.get(db, experience_id)
    if not experience:
        raise NotFoundException(f"经验不存在: {experience_id}")
    
    await experience_crud.delete(db, id=experience_id)
    return success_response(message="经验已删除")


@router.delete("/experiences", summary="清空经验库")
async def delete_all_experiences(
    category: Optional[str] = Query(None, description="按类别清空"),
    db: AsyncSession = Depends(get_db),
):
    """清空经验库"""
    from app.crud import experience_crud
    
    if category:
        experiences = await experience_crud.get_all_by_category(db, category)
    else:
        experiences = await experience_crud.get_multi(db, limit=1000)
    
    count = 0
    for exp in experiences:
        await experience_crud.delete(db, id=exp.id)
        count += 1
    
    return success_response(data={"deleted_count": count}, message=f"已删除 {count} 条经验")


@router.post("/experiences", summary="手动添加经验")
async def create_experience(
    category: str = Query(..., description="类别: screening/interview/analysis"),
    learned_rule: str = Query(..., description="经验规则"),
    context_summary: str = Query("手动添加", description="上下文摘要"),
    db: AsyncSession = Depends(get_db),
):
    """手动添加一条经验规则"""
    from app.crud import experience_crud
    from app.models import AgentExperienceCreate, ExperienceCategory
    
    if category not in [e.value for e in ExperienceCategory]:
        raise BadRequestException(f"无效类别: {category}")
    
    experience_data = AgentExperienceCreate(
        category=category,
        source_feedback="[手动添加]",
        learned_rule=learned_rule,
        context_summary=context_summary,
        embedding=None,
    )
    
    experience = await experience_crud.create(db, obj_in=experience_data)
    return success_response(
        data={"id": experience.id, "learned_rule": experience.learned_rule},
        message="经验已添加"
    )


async def _regenerate_report(db, category, target_id, experience_manager):
    """重新生成报告"""
    try:
        if category == ExperienceCategory.SCREENING.value:
            return await _regenerate_screening_report(db, target_id, experience_manager)
        elif category == ExperienceCategory.INTERVIEW.value:
            return await _regenerate_interview_report(db, target_id, experience_manager)
        elif category == ExperienceCategory.ANALYSIS.value:
            return await _regenerate_analysis_report(db, target_id, experience_manager)
    except Exception as exc:
        logger.error("报告重生成失败: {}", exc)
        return None
    return None


async def _regenerate_screening_report(db, task_id, experience_manager):
    """重生成筛选报告"""
    from app.agents import get_llm_client
    
    task = await screening_crud.get_with_application(db, task_id)
    if not task or not task.application:
        return None
    
    context = f"筛选报告 - 岗位: {task.application.position.title if task.application.position else '未知'}"
    experiences = await experience_manager.recall(db, "screening", context, top_k=5)
    experience_text = experience_manager.format_experiences_for_prompt(experiences)
    
    llm = get_llm_client()
    system_prompt = f"""你是一位专业的 HR 评估专家。{experience_text}
请生成简洁的筛选摘要（2-3句话）。"""

    user_prompt = f"""岗位: {task.application.position.title if task.application.position else '未知'}
候选人: {task.application.resume.candidate_name if task.application.resume else '未知'}
评分: {task.score}
原摘要: {task.summary or '无'}
请重新生成："""

    new_summary = await llm.complete(system_prompt, user_prompt, temperature=0.4)
    task.summary = new_summary
    await db.commit()
    return new_summary


async def _regenerate_interview_report(db, session_id, experience_manager):
    """重生成面试报告"""
    from app.agents import InterviewService
    from app.models import InterviewSessionUpdate
    
    session = await interview_crud.get_with_application(db, session_id)
    if not session:
        return None
    
    context = f"面试报告 - 岗位: {session.application.position.title if session.application and session.application.position else '未知'}"
    experiences = await experience_manager.recall(db, "interview", context, top_k=5)
    experience_text = experience_manager.format_experiences_for_prompt(experiences)
    
    job_config = {}
    candidate_name = "候选人"
    if session.application:
        if session.application.position:
            job_config = {"title": session.application.position.title}
        if session.application.resume:
            candidate_name = session.application.resume.candidate_name
    
    agent = InterviewService(job_config)
    hr_notes = f"{experience_text}\n\n请基于以上经验重新评估。"
    
    report = await agent.generate_final_report(
        candidate_name=candidate_name,
        messages=session.messages or [],
        hr_notes=hr_notes
    )
    
    new_report_md = _format_report_markdown(report, candidate_name)
    final_score = report.get("overall_assessment", {}).get("recommendation_score", 0)
    
    update_data = InterviewSessionUpdate(
        is_completed=True, final_score=final_score,
        report=report, report_markdown=new_report_md
    )
    await interview_crud.update(db, db_obj=session, obj_in=update_data)
    return new_report_md


async def _regenerate_analysis_report(db, analysis_id, experience_manager):
    """重生成综合分析报告"""
    from app.agents import get_llm_client
    from app.models import ComprehensiveAnalysisUpdate
    
    analysis = await analysis_crud.get_with_application(db, analysis_id)
    if not analysis:
        return None
    
    context = f"综合分析 - 岗位: {analysis.application.position.title if analysis.application and analysis.application.position else '未知'}"
    experiences = await experience_manager.recall(db, "analysis", context, top_k=5)
    experience_text = experience_manager.format_experiences_for_prompt(experiences)
    
    llm = get_llm_client()
    candidate_name = analysis.application.resume.candidate_name if analysis.application and analysis.application.resume else "候选人"
    
    system_prompt = f"""你是一位资深 HR 决策专家。{experience_text}
请生成专业的综合分析报告（Markdown 格式）。"""

    user_prompt = f"""候选人: {candidate_name}
岗位: {analysis.application.position.title if analysis.application and analysis.application.position else '未知'}
综合得分: {analysis.final_score}
推荐等级: {analysis.recommendation_level}
请重新生成："""

    new_report = await llm.complete(system_prompt, user_prompt, temperature=0.4)
    
    update_data = ComprehensiveAnalysisUpdate(report=new_report)
    await analysis_crud.update(db, db_obj=analysis, obj_in=update_data)
    return new_report


def _format_report_markdown(report: dict, candidate_name: str) -> str:
    """格式化面试报告为 Markdown"""
    overall = report.get("overall_assessment", {})
    md = f"# {candidate_name} 面试评估报告\n\n"
    md += f"- **推荐分数**: {overall.get('recommendation_score', 0)}/100\n"
    md += f"- **推荐建议**: {overall.get('recommendation', '待定')}\n"
    md += f"- **总结**: {overall.get('summary', '')}\n"
    return md


async def _get_context(db, category, target_id):
    """获取上下文信息"""
    if category == ExperienceCategory.SCREENING.value:
        task = await screening_crud.get_with_application(db, target_id)
        if not task:
            raise NotFoundException(f"筛选任务不存在: {target_id}")
        return f"筛选任务 - 岗位: {task.application.position.title if task.application and task.application.position else '未知'}"
    
    elif category == ExperienceCategory.INTERVIEW.value:
        session = await interview_crud.get_with_application(db, target_id)
        if not session:
            raise NotFoundException(f"面试会话不存在: {target_id}")
        return f"面试会话 - 岗位: {session.application.position.title if session.application and session.application.position else '未知'}"
    
    elif category == ExperienceCategory.ANALYSIS.value:
        analysis = await analysis_crud.get_with_application(db, target_id)
        if not analysis:
            raise NotFoundException(f"综合分析不存在: {target_id}")
        return f"综合分析 - 岗位: {analysis.application.position.title if analysis.application and analysis.application.position else '未知'}"
    
    return f"目标 ID: {target_id}"
