"""
AI 服务 API 路由

提供以下AI功能：
- 智能岗位需求生成
- 智能简历初筛
- 智能面试问题生成
- 智能回答评估
- 智能综合评估
- 开发测试工具
"""
import json
import asyncio
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import success_response, ResponseModel, DictResponse
from app.core.exceptions import NotFoundException, BadRequestException
from app.crud import position_crud, application_crud, screening_crud, interview_crud, resume_crud
from app.schemas.resume import ResumeCreate
from app.services.agents import (
    get_position_ai_service,
    get_llm_status,
    validate_llm_config,
    ScreeningAgentManager,
    InterviewAssistAgent,
    get_interview_assist_agent,
    CandidateComprehensiveAnalyzer,
    DevToolsService,
    get_dev_tools_service,
    get_task_limiter,
)

router = APIRouter()


# ============ 请求/响应模型 ============

class PositionGenerateRequest(BaseModel):
    """岗位需求生成请求"""
    description: str = Field(..., description="岗位描述（一句话或详细说明）")
    documents: Optional[List[Dict[str, str]]] = Field(None, description="参考文档列表")


class ScreeningStartRequest(BaseModel):
    """简历筛选启动请求"""
    application_id: str = Field(..., description="应聘申请ID")


class InterviewQuestionsRequest(BaseModel):
    """面试问题生成请求"""
    session_id: str = Field(..., description="面试会话ID")
    resume_content: Optional[str] = Field(None, description="简历内容")
    count: int = Field(3, ge=1, le=10, description="问题数量")
    interest_point_count: int = Field(2, ge=1, le=5, description="兴趣点数量")


class AnswerEvaluateRequest(BaseModel):
    """回答评估请求"""
    question: str = Field(..., description="面试问题")
    answer: str = Field(..., description="候选人回答")
    target_skills: Optional[List[str]] = Field(None, description="目标技能")
    difficulty: int = Field(5, ge=1, le=10, description="问题难度")


class CandidateQuestionsRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="面试会话ID，用于查询上下文")
    current_question: str = Field(..., description="当前问题")
    current_answer: str = Field(..., description="当前回答")
    conversation_history: Optional[List[Dict]] = Field(None, description="历史对话")
    resume_summary: Optional[str] = Field(None, description="简历摘要")
    followup_count: int = Field(2, description="追问数量")
    alternative_count: int = Field(3, description="候选问题数量")


class FinalReportRequest(BaseModel):
    """最终报告生成请求"""
    session_id: str = Field(..., description="面试会话ID")
    hr_notes: Optional[str] = Field("", description="HR备注")


class ComprehensiveAnalysisRequest(BaseModel):
    """综合分析请求"""
    application_id: str = Field(..., description="应聘申请ID")


class RandomResumeRequest(BaseModel):
    """随机简历生成请求"""
    position_id: str = Field(..., description="岗位ID")
    count: int = Field(1, ge=1, le=10, description="生成数量")


# ============ LLM 状态 ============

@router.get("/status", summary="获取LLM服务状态", response_model=DictResponse)
async def get_ai_status():
    """
    获取AI/LLM服务配置状态
    """
    status = get_llm_status()
    status["is_configured"] = validate_llm_config()
    return success_response(data=status)


# ============ 岗位需求生成 ============

@router.post("/position/generate", summary="AI生成岗位需求", response_model=DictResponse)
async def ai_generate_position(data: PositionGenerateRequest):
    """
    根据描述使用AI生成结构化的岗位需求
    
    输入可以是简短的一句话（如"招一个Python后端"），
    也可以是详细的需求说明，AI会生成完整的岗位要求JSON。
    """
    if not validate_llm_config():
        raise BadRequestException("LLM服务未配置，请检查API Key")
    
    try:
        service = get_position_ai_service()
        position_data = await service.generate_position_requirements(
            description=data.description,
            documents=data.documents
        )
        return success_response(
            data=position_data,
            message="岗位需求生成成功"
        )
    except ValueError as e:
        raise BadRequestException(str(e))


# ============ 简历筛选 ============

async def run_screening_task(
    task_id: str,
    criteria: Dict[str, Any],
    candidate_name: str,
    resume_content: str,
    db_url: str
):
    """
    后台运行简历筛选任务
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.core.progress_cache import progress_cache
    
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # 获取任务并发限制器
    task_limiter = get_task_limiter()
    
    async def update_status(status: str):
        """更新任务状态到数据库"""
        async with async_session() as session:
            task = await screening_crud.get(session, task_id)
            if task:
                task.status = status
                await session.commit()
    
    try:
        # 等待获取任务槽位（并发控制）
        progress_cache.update(task_id, progress=2, current_speaker="等待排队")
        loop = asyncio.get_event_loop()
        acquired = await loop.run_in_executor(None, task_limiter.wait_and_acquire, 300.0)
        if not acquired:
            raise RuntimeError("任务排队超时，请稍后重试")
        
        # 初始化进度缓存
        progress_cache.update(task_id, progress=5, current_speaker="初始化")
        
        # 创建筛选代理管理器
        manager = ScreeningAgentManager(criteria)
        manager.set_task_id(task_id)  # 设置任务ID以便进度跟踪
        manager.setup()
        
        # 运行筛选（这是同步操作，在线程池中运行）
        # Agent 切换时会自动通过 progress_cache 更新进度
        loop = asyncio.get_event_loop()
        messages = await loop.run_in_executor(
            None,
            manager.run_screening,
            candidate_name,
            resume_content
        )
        
        # 解析结果
        result = _parse_screening_result(messages)
        
        # 更新数据库（仅最终结果）
        async with async_session() as session:
            task = await screening_crud.get(session, task_id)
            if task:
                task.status = "completed"
                task.score = result.get("comprehensive_score", 0)
                task.dimension_scores = result.get("dimension_scores")
                task.summary = result.get("summary", "")
                await session.commit()
                
    except Exception as e:
        async with async_session() as session:
            task = await screening_crud.get(session, task_id)
            if task:
                task.status = "failed"
                task.error_message = str(e)
                await session.commit()
    finally:
        # 释放任务槽位
        task_limiter.release()
        # 清理进度缓存
        progress_cache.remove(task_id)
        await engine.dispose()


def _parse_screening_result(messages: List[Dict]) -> Dict[str, Any]:
    """解析筛选消息获取评分结果"""
    import re
    
    result = {
        "comprehensive_score": 0,
        "summary": "",
        "dimension_scores": {
            "hr_score": None,
            "technical_score": None,
            "manager_score": None
        }
    }
    
    # 遍历所有消息提取各维度评分
    for msg in messages:
        content = msg.get("content", "")
        if not content:
            continue
        
        # 提取HR评分（格式：HR评分：85分）
        hr_match = re.search(r'HR评分[：:]\s*(\d+)', content)
        if hr_match and result["dimension_scores"]["hr_score"] is None:
            result["dimension_scores"]["hr_score"] = int(hr_match.group(1))
        
        # 提取技术评分（格式：技术评分：90分）
        tech_match = re.search(r'技术评分[：:]\s*(\d+)', content)
        if tech_match and result["dimension_scores"]["technical_score"] is None:
            result["dimension_scores"]["technical_score"] = int(tech_match.group(1))
        
        # 提取管理评分（格式：管理评分：80分）
        mgr_match = re.search(r'管理评分[：:]\s*(\d+)', content)
        if mgr_match and result["dimension_scores"]["manager_score"] is None:
            result["dimension_scores"]["manager_score"] = int(mgr_match.group(1))
        
        # 提取综合评分（格式：综合评分：85分）
        if "综合评分" in content:
            match = re.search(r'综合评分[：:]\s*(\d+)', content)
            if match:
                result["comprehensive_score"] = int(match.group(1))
            result["summary"] = content
    
    return result


@router.post("/screening/start", summary="启动AI简历筛选", response_model=DictResponse)
async def start_ai_screening(
    data: ScreeningStartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    启动AI简历筛选任务（后台运行）
    
    使用多Agent协作进行简历评审：
    - HR专家：评估综合素质
    - 技术专家：评估技术能力
    - 项目经理：评估管理能力
    - 综合评审：汇总给出最终建议
    """
    if not validate_llm_config():
        raise BadRequestException("LLM服务未配置，请检查API Key")
    
    # 获取应聘申请详情
    application = await application_crud.get_detail(db, data.application_id)
    if not application:
        raise NotFoundException(f"应聘申请不存在: {data.application_id}")
    
    if not application.resume:
        raise BadRequestException("该申请没有关联简历")
    if not application.position:
        raise BadRequestException("该申请没有关联岗位")
    
    # 检查是否已存在筛选任务
    existing_task = await screening_crud.get_by_application(db, data.application_id)
    if existing_task:
        if existing_task.status == "running":
            return success_response(
                data={
                    "task_id": existing_task.id,
                    "status": "processing",
                    "message": "筛选任务正在进行中"
                },
                message="筛选任务正在进行中"
            )
        # 如果已完成或失败，删除旧任务重新创建
        await db.delete(existing_task)
        await db.flush()
    
    # 构建筛选条件
    position = application.position
    criteria = {
        "position": position.title,
        "description": position.description or "",
        "required_skills": position.required_skills or [],
        "optional_skills": position.optional_skills or [],
        "min_experience": position.min_experience or 0,
        "education": position.education or [],
        "salary_range": [position.salary_min or 0, position.salary_max or 0],
    }
    
    # 创建筛选任务
    from app.schemas.screening import ScreeningTaskCreate
    task_data = ScreeningTaskCreate(application_id=data.application_id)
    task = await screening_crud.create_task(db, obj_in=task_data)
    
    # 更新状态为处理中（使用 running 与前端保持一致）
    task.status = "running"
    task.progress = 5
    await db.commit()
    
    # 后台运行筛选任务
    from app.core.config import settings
    background_tasks.add_task(
        run_screening_task,
        task.id,
        criteria,
        application.resume.candidate_name,
        application.resume.content or "",
        settings.database_url
    )
    
    return success_response(
        data={
            "task_id": task.id,
            "status": "processing",
            "message": "筛选任务已启动，请轮询状态接口获取进度"
        },
        message="筛选任务已启动"
    )


# ============ 面试问题生成 ============

@router.post("/interview/initial-questions", summary="AI生成初始面试问题", response_model=DictResponse)
async def ai_generate_initial_questions(
    data: InterviewQuestionsRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    根据简历和岗位要求生成针对性的面试问题
    
    返回：
    - questions: 面试问题列表
    - interest_points: 简历中值得关注的兴趣点
    """
    if not validate_llm_config():
        raise BadRequestException("LLM服务未配置，请检查API Key")
    
    # 获取会话信息
    session = await interview_crud.get_with_application(db, data.session_id)
    if not session:
        raise NotFoundException(f"面试会话不存在: {data.session_id}")
    
    # 构建job_config
    job_config = {}
    if session.application and session.application.position:
        pos = session.application.position
        job_config = {
            "title": pos.title,
            "description": pos.description or "",
            "requirements": {
                "required_skills": pos.required_skills or [],
                "optional_skills": pos.optional_skills or [],
                "min_experience": pos.min_experience or 0,
                "education": pos.education or [],
            }
        }
    
    # 获取简历内容
    resume_content = data.resume_content
    if not resume_content and session.application and session.application.resume:
        resume_content = session.application.resume.content or ""
    
    agent = get_interview_assist_agent(job_config)
    result = await agent.generate_initial_questions(
        resume_content=resume_content,
        count=data.count,
        interest_point_count=data.interest_point_count
    )
    
    # 更新会话的问题池
    from app.schemas.interview import InterviewSessionUpdate
    questions_text = [q["question"] for q in result.get("questions", [])]
    update_data = InterviewSessionUpdate(question_pool=questions_text)
    await interview_crud.update_session(db, db_obj=session, obj_in=update_data)
    
    return success_response(data=result)


@router.post("/interview/evaluate", summary="AI评估回答", response_model=DictResponse)
async def ai_evaluate_answer(data: AnswerEvaluateRequest):
    """
    AI评估候选人的回答质量
    
    返回多维度评分：
    - 技术深度、实践经验、回答具体性
    - 逻辑清晰度、诚实度、沟通能力
    - 是否需要追问及建议
    """
    if not validate_llm_config():
        raise BadRequestException("LLM服务未配置，请检查API Key")
    
    agent = get_interview_assist_agent()
    result = await agent.evaluate_answer(
        question=data.question,
        answer=data.answer,
        target_skills=data.target_skills,
        difficulty=data.difficulty
    )
    
    return success_response(data=result)


@router.post("/interview/adaptive-questions", summary="AI生成自适应问题", response_model=DictResponse)
async def ai_generate_adaptive_questions(
    data: CandidateQuestionsRequest,
    db: AsyncSession = Depends(get_db),
):
    if not validate_llm_config():
        raise BadRequestException("LLM服务未配置，请检查API Key")
    
    job_config = {}
    resume_summary = data.resume_summary or ""
    
    if data.session_id:
        session = await interview_crud.get_with_application(db, data.session_id)
        if session and session.application:
            if session.application.position:
                pos = session.application.position
                job_config = {
                    "title": pos.title,
                    "description": pos.description or "",
                    "requirements": {
                        "required_skills": pos.required_skills or [],
                        "optional_skills": pos.optional_skills or [],
                    }
                }
            if session.application.resume and not resume_summary:
                resume_summary = session.application.resume.content or ""
                if len(resume_summary) > 2000:
                    resume_summary = resume_summary[:2000] + "..."
    
    agent = get_interview_assist_agent(job_config)
    result = await agent.generate_adaptive_questions(
        current_question=data.current_question,
        current_answer=data.current_answer,
        conversation_history=data.conversation_history,
        resume_summary=resume_summary,
        followup_count=data.followup_count,
        alternative_count=data.alternative_count
    )
    
    followups = [q for q in result if q.get("source") == "followup"]
    alternatives = [q for q in result if q.get("source") in ("resume", "job")]
    
    return success_response(data={
        "candidate_questions": result,
        "followups": followups,
        "alternatives": alternatives
    })


@router.post("/interview/report", summary="AI生成面试报告", response_model=DictResponse)
async def ai_generate_report(
    data: FinalReportRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    生成最终面试评估报告
    
    基于整场面试问答记录，生成包含：
    - 综合评分和推荐建议
    - 各维度分析
    - 技能评估
    - 亮点和风险点
    """
    if not validate_llm_config():
        raise BadRequestException("LLM服务未配置，请检查API Key")
    
    # 获取会话信息
    session = await interview_crud.get_with_application(db, data.session_id)
    if not session:
        raise NotFoundException(f"面试会话不存在: {data.session_id}")
    
    if not session.messages:
        raise BadRequestException("没有问答消息，无法生成报告")
    
    # 构建job_config
    job_config = {}
    candidate_name = "候选人"
    if session.application:
        if session.application.position:
            pos = session.application.position
            job_config = {"title": pos.title}
        if session.application.resume:
            candidate_name = session.application.resume.candidate_name
    
    agent = get_interview_assist_agent(job_config)
    report = await agent.generate_final_report(
        candidate_name=candidate_name,
        messages=session.messages,
        hr_notes=data.hr_notes
    )
    
    # 更新会话
    from app.schemas.interview import InterviewSessionUpdate
    final_score = report.get("overall_assessment", {}).get("recommendation_score", 0)
    update_data = InterviewSessionUpdate(
        is_completed=True,
        final_score=final_score,
        report=report,
        report_markdown=_format_report_markdown(report, candidate_name)
    )
    await interview_crud.update_session(db, db_obj=session, obj_in=update_data)
    
    return success_response(data=report, message="面试报告生成成功")


def _format_report_markdown(report: Dict, candidate_name: str) -> str:
    """格式化报告为Markdown"""
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


# ============ 综合分析 ============

@router.post("/analysis/comprehensive", summary="AI综合分析评估", response_model=DictResponse)
async def ai_comprehensive_analysis(
    data: ComprehensiveAnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    整合简历、筛选报告、面试记录进行综合评估
    
    基于Rubric量表进行多维度评估：
    - 专业能力、工作经验、软技能
    - 文化匹配、面试表现
    
    输出最终录用建议。
    """
    if not validate_llm_config():
        raise BadRequestException("LLM服务未配置，请检查API Key")
    
    # 获取应聘申请详情
    application = await application_crud.get_detail(db, data.application_id)
    if not application:
        raise NotFoundException(f"应聘申请不存在: {data.application_id}")
    
    # 收集数据
    resume_content = ""
    candidate_name = "候选人"
    job_config = {}
    
    if application.resume:
        resume_content = application.resume.content or ""
        candidate_name = application.resume.candidate_name
    
    if application.position:
        job_config = {"title": application.position.title}
    
    # 获取筛选报告 (1:1 关系)
    screening_report = {}
    screening_task = await screening_crud.get_by_application(db, data.application_id)
    if screening_task:
        screening_report = {
            "comprehensive_score": screening_task.score,
            "summary": screening_task.summary,
        }
    
    # 获取面试记录 (1:1 关系)
    interview_records = []
    interview_report = {}
    interview_session = await interview_crud.get_by_application(db, data.application_id)
    if interview_session:
        interview_records = interview_session.messages or []
        interview_report = interview_session.report or {}
    
    # 执行综合分析
    analyzer = CandidateComprehensiveAnalyzer(job_config)
    result = await analyzer.analyze(
        candidate_name=candidate_name,
        resume_content=resume_content,
        screening_report=screening_report,
        interview_records=interview_records,
        interview_report=interview_report,
    )
    
    return success_response(data=result, message="综合分析完成")


# ============ 开发测试工具 ============

@router.post("/dev/random-resume", summary="生成随机简历（测试用）", response_model=DictResponse)
async def generate_random_resume(
    data: RandomResumeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    根据岗位要求生成随机简历（仅用于开发测试）
    
    生成的简历有一定随机性，匹配度随机（优秀/一般/不匹配）
    """
    if not validate_llm_config():
        raise BadRequestException("LLM服务未配置，请检查API Key")
    
    # 获取岗位信息
    position = await position_crud.get(db, data.position_id)
    if not position:
        raise NotFoundException(f"岗位不存在: {data.position_id}")
    
    position_data = {
        "position": position.title,
        "description": position.description or "",
        "required_skills": position.required_skills or [],
        "optional_skills": position.optional_skills or [],
        "min_experience": position.min_experience or 0,
        "education": position.education or [],
    }
    
    # 生成简历
    service = get_dev_tools_service()
    if data.count == 1:
        resume = await service.generate_random_resume(position_data)
        resumes = [resume]
    else:
        resumes = await service.generate_batch_resumes(position_data, data.count)
    
    # 将生成的简历保存到数据库
    saved_resumes = []
    skipped_resumes = []
    for resume_data in resumes:
        # 检查是否已存在（通过文件哈希去重）
        if await resume_crud.check_hash_exists(db, resume_data['file_hash']):
            skipped_resumes.append({
                'name': resume_data['name'],
                'reason': '简历已存在（哈希重复）'
            })
            continue
        
        # 创建简历记录
        resume_create = ResumeCreate(
            candidate_name=resume_data['candidate_name'],
            content=resume_data['content'],
            filename=resume_data['name'],
            file_hash=resume_data['file_hash'],
            file_size=len(resume_data['content'].encode('utf-8')),
            notes=f"AI随机生成 - 目标岗位: {position.title}"
        )
        saved_resume = await resume_crud.create_resume(db, obj_in=resume_create)
        saved_resumes.append({
            'id': saved_resume.id,
            'candidate_name': saved_resume.candidate_name,
            'filename': saved_resume.filename
        })
    
    return success_response(
        data={
            "resumes": resumes,
            "added": saved_resumes,
            "skipped": skipped_resumes,
            "added_count": len(saved_resumes),
            "skipped_count": len(skipped_resumes)
        },
        message=f"成功生成 {len(resumes)} 份随机简历，已保存 {len(saved_resumes)} 份到简历库"
    )
