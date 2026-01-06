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
    
    流程：
    1. 验证目标报告存在
    2. 提取上下文信息
    3. 调用 ExperienceManager.learn() 学习经验
    4. 检索所有相关经验
    5. 注入经验重新生成报告
    
    Args:
        data.category: 报告类别 (screening/interview/analysis)
        data.target_id: 目标 ID
        data.feedback: HR 反馈内容
        regenerate: 是否立即重新生成报告（默认 True）
    """
    # 验证 LLM 配置
    if not get_llm_client().is_configured():
        raise BadRequestException("LLM服务未配置，请检查API Key")
    
    # 验证类别
    if data.category not in [e.value for e in ExperienceCategory]:
        raise BadRequestException(f"无效的类别: {data.category}，支持: screening/interview/analysis")
    
    # 根据类别获取上下文
    context = await _get_context(db, data.category, data.target_id)
    
    # 学习经验
    experience_manager = get_experience_manager()
    experience = await experience_manager.learn(
        db=db,
        category=data.category,
        feedback=data.feedback,
        context=context,
    )
    
    logger.info(
        "经验学习完成: category={}, target_id={}, experience_id={}",
        data.category, data.target_id, experience.id
    )
    
    # 重新生成报告
    new_report = None
    if regenerate:
        new_report = await _regenerate_report(
            db=db,
            category=data.category,
            target_id=data.target_id,
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
    """
    获取已学习的经验列表
    
    Args:
        category: 可选，按类别筛选
    """
    from app.crud import experience_crud
    from app.models import AgentExperienceResponse
    
    if category:
        experiences = await experience_crud.get_by_category(db, category, limit=50)
    else:
        experiences = await experience_crud.get_multi(db, limit=50)
    
    items = [AgentExperienceResponse.model_validate(exp).model_dump() for exp in experiences]
    
    return success_response(data={
        "items": items,
        "total": len(items),
    })


async def _regenerate_report(
    db: AsyncSession,
    category: str,
    target_id: str,
    experience_manager,
) -> Optional[str]:
    """
    根据类别重新生成报告
    
    流程：
    1. 检索该类别的所有相关经验
    2. 格式化为 Prompt 注入内容
    3. 调用对应的 Agent 重新生成
    4. 更新数据库记录
    """
    try:
        if category == ExperienceCategory.SCREENING.value:
            return await _regenerate_screening_report(db, target_id, experience_manager)
        elif category == ExperienceCategory.INTERVIEW.value:
            return await _regenerate_interview_report(db, target_id, experience_manager)
        elif category == ExperienceCategory.ANALYSIS.value:
            return await _regenerate_analysis_report(db, target_id, experience_manager)
    except Exception as exc:
        logger.error("报告重生成失败: category={}, target_id={}, error={}", category, target_id, exc)
        return None
    
    return None


async def _regenerate_screening_report(
    db: AsyncSession,
    task_id: str,
    experience_manager,
) -> Optional[str]:
    """重生成筛选报告"""
    from app.agents import get_llm_client
    from app.agents.prompts import get_prompt
    
    task = await screening_crud.get_with_application(db, task_id)
    if not task or not task.application:
        return None
    
    # 获取相关经验
    context = f"筛选报告 - 岗位: {task.application.position.title if task.application.position else '未知'}"
    experiences = await experience_manager.recall(db, "screening", context, top_k=5)
    experience_text = experience_manager.format_experiences_for_prompt(experiences)
    
    # 构建重生成 Prompt
    llm = get_llm_client()
    
    system_prompt = f"""你是一位专业的 HR 评估专家。请根据以下信息重新生成筛选报告摘要。

{experience_text}

请生成简洁、专业的筛选摘要（2-3句话），包含：
1. 候选人与岗位的匹配度评价
2. 主要优势或不足
3. 推荐结论（推荐面试/备选/不推荐）
"""

    user_prompt = f"""岗位: {task.application.position.title if task.application.position else '未知'}
候选人: {task.application.resume.candidate_name if task.application.resume else '未知'}
当前评分: {task.score}
原摘要: {task.summary or '无'}

请重新生成筛选摘要："""

    new_summary = await llm.complete(system_prompt, user_prompt, temperature=0.4)
    
    # 更新数据库
    task.summary = new_summary
    await db.commit()
    
    logger.info("筛选报告已重生成: task_id={}", task_id)
    return new_summary


async def _regenerate_interview_report(
    db: AsyncSession,
    session_id: str,
    experience_manager,
) -> Optional[str]:
    """重生成面试报告"""
    from app.agents import InterviewService
    from app.models import InterviewSessionUpdate
    
    session = await interview_crud.get_with_application(db, session_id)
    if not session:
        return None
    
    # 获取相关经验
    context = f"面试报告 - 岗位: {session.application.position.title if session.application and session.application.position else '未知'}"
    experiences = await experience_manager.recall(db, "interview", context, top_k=5)
    experience_text = experience_manager.format_experiences_for_prompt(experiences)
    
    # 构建 job_config
    job_config = {}
    candidate_name = "候选人"
    if session.application:
        if session.application.position:
            job_config = {"title": session.application.position.title}
        if session.application.resume:
            candidate_name = session.application.resume.candidate_name
    
    # 使用 InterviewService 重生成报告
    agent = InterviewService(job_config)
    
    # 注入经验到 HR notes
    hr_notes_with_experience = f"{experience_text}\n\n请基于以上经验重新评估候选人表现。"
    
    report = await agent.generate_final_report(
        candidate_name=candidate_name,
        messages=session.messages or [],
        hr_notes=hr_notes_with_experience
    )
    
    # 格式化为 Markdown
    new_report_md = _format_report_markdown(report, candidate_name)
    
    # 更新数据库
    final_score = report.get("overall_assessment", {}).get("recommendation_score", 0)
    update_data = InterviewSessionUpdate(
        is_completed=True,
        final_score=final_score,
        report=report,
        report_markdown=new_report_md
    )
    await interview_crud.update(db, db_obj=session, obj_in=update_data)
    
    logger.info("面试报告已重生成: session_id={}", session_id)
    return new_report_md


async def _regenerate_analysis_report(
    db: AsyncSession,
    analysis_id: str,
    experience_manager,
) -> Optional[str]:
    """重生成综合分析报告"""
    from app.agents import get_llm_client
    from app.models import ComprehensiveAnalysisUpdate
    
    analysis = await analysis_crud.get_with_application(db, analysis_id)
    if not analysis:
        return None
    
    # 获取相关经验
    context = f"综合分析 - 岗位: {analysis.application.position.title if analysis.application and analysis.application.position else '未知'}"
    experiences = await experience_manager.recall(db, "analysis", context, top_k=5)
    experience_text = experience_manager.format_experiences_for_prompt(experiences)
    
    # 构建重生成 Prompt
    llm = get_llm_client()
    
    candidate_name = "候选人"
    if analysis.application and analysis.application.resume:
        candidate_name = analysis.application.resume.candidate_name
    
    system_prompt = f"""你是一位资深 HR 决策专家。请根据以下信息重新生成综合分析报告。

{experience_text}

请生成专业的综合分析报告（Markdown 格式），包含：
1. 候选人综合评价（一句话）
2. 核心优势（2-3点）
3. 潜在风险（1-2点）
4. 最终录用建议
"""

    user_prompt = f"""候选人: {candidate_name}
岗位: {analysis.application.position.title if analysis.application and analysis.application.position else '未知'}
综合得分: {analysis.final_score}
推荐等级: {analysis.recommendation_level}
原报告: {analysis.report or '无'}

请重新生成综合分析报告："""

    new_report = await llm.complete(system_prompt, user_prompt, temperature=0.4)
    
    # 更新数据库
    update_data = ComprehensiveAnalysisUpdate(report=new_report)
    await analysis_crud.update(db, db_obj=analysis, obj_in=update_data)
    
    logger.info("综合分析报告已重生成: analysis_id={}", analysis_id)
    return new_report


def _format_report_markdown(report: dict, candidate_name: str) -> str:
    """格式化面试报告为 Markdown"""
    overall = report.get("overall_assessment", {})
    
    md = f"# {candidate_name} 面试评估报告\n\n"
    md += f"## 综合评估\n"
    md += f"- **推荐分数**: {overall.get('recommendation_score', 0)}/100\n"
    md += f"- **推荐建议**: {overall.get('recommendation', '待定')}\n"
    md += f"- **总结**: {overall.get('summary', '')}\n\n"
    
    if report.get("highlights"):
        md += "## 亮点\n"
        for h in report["highlights"]:
            md += f"- {h}\n"
        md += "\n"
    
    if report.get("red_flags"):
        md += "## 风险点\n"
        for r in report["red_flags"]:
            md += f"- {r}\n"
        md += "\n"
    
    return md


async def _get_context(db: AsyncSession, category: str, target_id: str) -> str:
    """
    根据类别和目标 ID 获取上下文信息
    """
    if category == ExperienceCategory.SCREENING.value:
        task = await screening_crud.get_with_application(db, target_id)
        if not task:
            raise NotFoundException(f"筛选任务不存在: {target_id}")
        
        context_parts = [f"筛选任务 ID: {target_id}"]
        if task.application and task.application.position:
            context_parts.append(f"岗位: {task.application.position.title}")
        if task.summary:
            context_parts.append(f"筛选摘要: {task.summary}")
        if task.recommendation:
            context_parts.append(f"推荐结果: {task.recommendation}")
        
        return "\n".join(context_parts)
    
    elif category == ExperienceCategory.INTERVIEW.value:
        session = await interview_crud.get_with_application(db, target_id)
        if not session:
            raise NotFoundException(f"面试会话不存在: {target_id}")
        
        context_parts = [f"面试会话 ID: {target_id}"]
        if session.application and session.application.position:
            context_parts.append(f"岗位: {session.application.position.title}")
        if session.is_completed:
            context_parts.append("面试状态: 已完成")
        if session.final_score:
            context_parts.append(f"面试评分: {session.final_score}")
        
        return "\n".join(context_parts)
    
    elif category == ExperienceCategory.ANALYSIS.value:
        analysis = await analysis_crud.get_with_application(db, target_id)
        if not analysis:
            raise NotFoundException(f"综合分析不存在: {target_id}")
        
        context_parts = [f"综合分析 ID: {target_id}"]
        if analysis.application and analysis.application.position:
            context_parts.append(f"岗位: {analysis.application.position.title}")
        context_parts.append(f"最终评分: {analysis.final_score}")
        context_parts.append(f"推荐等级: {analysis.recommendation_level}")
        
        return "\n".join(context_parts)
    
    return f"目标 ID: {target_id}"

