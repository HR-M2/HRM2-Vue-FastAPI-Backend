"""
面试辅助 API 路由
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
from app.crud import interview_crud, application_crud
from app.schemas.interview import (
    InterviewSessionCreate,
    InterviewSessionResponse,
    InterviewSessionUpdate,
    QARecordCreate,
    GenerateQuestionsRequest,
    QARecord,
)

router = APIRouter()


@router.get("", summary="获取面试会话列表", response_model=PagedResponseModel[InterviewSessionResponse])
async def get_interview_sessions(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    application_id: Optional[str] = Query(None, description="应聘申请ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取面试会话列表
    """
    skip = (page - 1) * page_size
    
    if application_id:
        sessions = await interview_crud.get_by_application(
            db, application_id, skip=skip, limit=page_size
        )
    else:
        sessions = await interview_crud.get_multi(db, skip=skip, limit=page_size)
    
    total = await interview_crud.count(db)
    
    items = []
    for s in sessions:
        item = InterviewSessionResponse.model_validate(s)
        item.current_round = s.current_round
        item.qa_records = [QARecord(**r) for r in (s.qa_records or [])]
        items.append(item.model_dump())
    
    return paged_response(items, total, page, page_size)


@router.post("", summary="创建面试会话", response_model=ResponseModel[InterviewSessionResponse])
async def create_interview_session(
    data: InterviewSessionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    创建新的面试会话
    """
    # 验证应聘申请存在
    application = await application_crud.get_detail(db, data.application_id)
    if not application:
        raise NotFoundException(f"应聘申请不存在: {data.application_id}")
    
    # 检查是否有进行中的会话
    active_session = await interview_crud.get_active_session(db, data.application_id)
    if active_session:
        raise BadRequestException("该申请已有进行中的面试会话")
    
    session = await interview_crud.create_session(db, obj_in=data)
    
    response = InterviewSessionResponse.model_validate(session)
    response.qa_records = []
    if application.resume:
        response.candidate_name = application.resume.candidate_name
    if application.position:
        response.position_title = application.position.title
    
    return success_response(
        data=response.model_dump(),
        message="面试会话创建成功"
    )


@router.get("/{session_id}", summary="获取面试会话详情", response_model=ResponseModel[InterviewSessionResponse])
async def get_interview_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取面试会话详情
    """
    session = await interview_crud.get_with_application(db, session_id)
    if not session:
        raise NotFoundException(f"面试会话不存在: {session_id}")
    
    response = InterviewSessionResponse.model_validate(session)
    response.current_round = session.current_round
    response.qa_records = [QARecord(**r) for r in (session.qa_records or [])]
    
    if session.application:
        if session.application.resume:
            response.candidate_name = session.application.resume.candidate_name
        if session.application.position:
            response.position_title = session.application.position.title
    
    return success_response(data=response.model_dump())


@router.post("/{session_id}/questions", summary="生成面试问题", response_model=DictResponse)
async def generate_questions(
    session_id: str,
    data: GenerateQuestionsRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    为面试会话生成问题池（AI 生成）
    
    注意: 实际 AI 生成逻辑需要在 services 层实现
    """
    session = await interview_crud.get_with_application(db, session_id)
    if not session:
        raise NotFoundException(f"面试会话不存在: {session_id}")
    
    if session.is_completed:
        raise BadRequestException("面试会话已结束")
    
    # TODO: 调用 AI 服务生成问题
    # 这里返回占位数据
    questions = [
        f"示例问题 {i+1}（难度: {data.difficulty}）"
        for i in range(data.count)
    ]
    
    # 更新问题池
    update_data = InterviewSessionUpdate(question_pool=questions)
    session = await interview_crud.update_session(
        db, db_obj=session, obj_in=update_data
    )
    
    return success_response(
        data={"questions": questions},
        message="问题生成成功"
    )


@router.post("/{session_id}/qa", summary="记录问答", response_model=DictResponse)
async def record_qa(
    session_id: str,
    data: QARecordCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    记录一轮问答
    """
    session = await interview_crud.get(db, session_id)
    if not session:
        raise NotFoundException(f"面试会话不存在: {session_id}")
    
    if session.is_completed:
        raise BadRequestException("面试会话已结束")
    
    session = await interview_crud.add_qa_record(
        db,
        db_obj=session,
        question=data.question,
        answer=data.answer,
        score=data.score,
        evaluation=data.evaluation,
    )
    
    return success_response(
        data={
            "current_round": session.current_round,
            "qa_records": session.qa_records,
        },
        message="问答记录成功"
    )


@router.post("/{session_id}/complete", summary="完成面试会话", response_model=ResponseModel[InterviewSessionResponse])
async def complete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    完成面试会话并生成报告
    
    注意: 实际报告生成逻辑需要在 services 层实现
    """
    session = await interview_crud.get(db, session_id)
    if not session:
        raise NotFoundException(f"面试会话不存在: {session_id}")
    
    if session.is_completed:
        raise BadRequestException("面试会话已结束")
    
    if not session.qa_records:
        raise BadRequestException("没有问答记录，无法完成会话")
    
    # TODO: 调用 AI 服务生成报告
    # 这里使用占位数据
    avg_score = sum(r.get("score", 0) or 0 for r in session.qa_records) / len(session.qa_records)
    
    update_data = InterviewSessionUpdate(
        is_completed=True,
        final_score=avg_score,
        report={"summary": "面试报告占位"},
        report_markdown="# 面试报告\n\n待 AI 服务生成..."
    )
    
    session = await interview_crud.update_session(
        db, db_obj=session, obj_in=update_data
    )
    
    response = InterviewSessionResponse.model_validate(session)
    response.qa_records = [QARecord(**r) for r in (session.qa_records or [])]
    
    return success_response(
        data=response.model_dump(),
        message="面试会话已完成"
    )


@router.delete("/{session_id}", summary="删除面试会话", response_model=MessageResponse)
async def delete_interview_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    删除面试会话
    """
    session = await interview_crud.get(db, session_id)
    if not session:
        raise NotFoundException(f"面试会话不存在: {session_id}")
    
    await interview_crud.delete(db, id=session_id)
    return success_response(message="面试会话删除成功")
