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
from app.models import (
    InterviewSessionCreate,
    InterviewSessionResponse,
    InterviewSessionUpdate,
    MessagesSyncRequest,
    GenerateQuestionsRequest,
    QAMessage,
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
        # 1:1 关系，直接获取单个会话
        session = await interview_crud.get_by_application(db, application_id)
        sessions = [session] if session else []
    else:
        sessions = await interview_crud.get_multi(db, skip=skip, limit=page_size)
    
    total = await interview_crud.count(db)
    
    items = []
    for s in sessions:
        item = InterviewSessionResponse.model_validate(s)
        item.message_count = s.message_count
        item.messages = [QAMessage(**m) for m in (s.messages or [])]
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
    application = await application_crud.get_with_relations(db, data.application_id)
    if not application:
        raise NotFoundException(f"应聘申请不存在: {data.application_id}")
    
    # 如已存在会话则先删除，每次开始新的面试
    existing_session = await interview_crud.get_by_application(db, data.application_id)
    if existing_session:
        await interview_crud.delete(db, id=existing_session.id)
    
    session = await interview_crud.create(db, obj_in=data)
    
    response = InterviewSessionResponse.model_validate(session)
    response.messages = []
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
    
    如果会话报告引用了历史经验，会返回经验的详细内容，
    便于用户了解 AI 的决策依据。
    """
    session = await interview_crud.get_with_application(db, session_id)
    if not session:
        raise NotFoundException(f"面试会话不存在: {session_id}")
    
    response = InterviewSessionResponse.model_validate(session)
    response.message_count = session.message_count
    response.messages = [QAMessage(**m) for m in (session.messages or [])]
    
    if session.application:
        if session.application.resume:
            response.candidate_name = session.application.resume.candidate_name
        if session.application.position:
            response.position_title = session.application.position.title
    
    # 如果有引用的经验 ID，获取经验详情
    if session.applied_experience_ids:
        from app.crud import experience_crud
        from app.models import AppliedExperienceItem
        experiences = await experience_crud.get_by_ids(db, session.applied_experience_ids)
        response.applied_experiences = [
            AppliedExperienceItem(
                id=exp.id,
                learned_rule=exp.learned_rule,
                source_feedback=exp.source_feedback,
                category=exp.category,
            )
            for exp in experiences
        ]
    
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
    session = await interview_crud.update(
        db, db_obj=session, obj_in=update_data
    )
    
    return success_response(
        data={"questions": questions},
        message="问题生成成功"
    )


@router.post("/{session_id}/sync", summary="同步对话记录", response_model=DictResponse)
async def sync_messages(
    session_id: str,
    data: MessagesSyncRequest,
    db: AsyncSession = Depends(get_db),
):
    session = await interview_crud.get(db, session_id)
    if not session:
        raise NotFoundException(f"面试会话不存在: {session_id}")
    
    if session.is_completed:
        raise BadRequestException("面试会话已结束")
    
    from datetime import datetime
    messages_data = []
    for i, msg in enumerate(data.messages):
        messages_data.append({
            "seq": i + 1,
            "role": msg.role,
            "content": msg.content,
            "timestamp": datetime.now().isoformat()
        })
    
    update_data = InterviewSessionUpdate()
    session.messages = messages_data
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(session, "messages")
    await db.flush()
    await db.refresh(session)
    
    return success_response(
        data={"message_count": len(messages_data)},
        message="对话记录同步成功"
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
    
    if not session.messages:
        raise BadRequestException("没有问答消息，无法完成会话")
    
    update_data = InterviewSessionUpdate(
        is_completed=True,
        report={"summary": "面试报告占位"},
        report_markdown="# 面试报告\n\n待 AI 服务生成..."
    )
    
    session = await interview_crud.update(
        db, db_obj=session, obj_in=update_data
    )
    
    response = InterviewSessionResponse.model_validate(session)
    response.messages = [QAMessage(**m) for m in (session.messages or [])]
    
    return success_response(
        data=response.model_dump(),
        message="面试会话已完成"
    )


@router.patch("/{session_id}", summary="更新面试会话", response_model=ResponseModel[InterviewSessionResponse])
async def update_interview_session(
    session_id: str,
    data: InterviewSessionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    更新面试会话（支持人工编辑报告）
    """
    session = await interview_crud.get(db, session_id)
    if not session:
        raise NotFoundException(f"面试会话不存在: {session_id}")
    
    session = await interview_crud.update(db, db_obj=session, obj_in=data)
    
    response = InterviewSessionResponse.model_validate(session)
    response.messages = [QAMessage(**m) for m in (session.messages or [])]
    response.message_count = session.message_count
    
    return success_response(
        data=response.model_dump(),
        message="面试会话更新成功"
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
