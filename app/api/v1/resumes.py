"""
简历管理 API 路由
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import success_response, paged_response
from app.core.exceptions import NotFoundException, ConflictException
from app.crud import resume_crud
from app.schemas.resume import (
    ResumeCreate,
    ResumeUpdate,
    ResumeResponse,
    ResumeListResponse,
)

router = APIRouter()


@router.get("", summary="获取简历列表")
async def get_resumes(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词(姓名)"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取简历列表，支持分页和关键词搜索
    """
    skip = (page - 1) * page_size
    
    if keyword:
        resumes = await resume_crud.get_by_candidate_name(
            db, keyword, skip=skip, limit=page_size
        )
        total = len(resumes)  # 简化处理
    else:
        resumes = await resume_crud.get_multi(db, skip=skip, limit=page_size)
        total = await resume_crud.count(db)
    
    items = []
    for r in resumes:
        item = ResumeListResponse.model_validate(r)
        item.application_count = len(r.applications) if r.applications else 0
        items.append(item.model_dump())
    
    return paged_response(items, total, page, page_size)


@router.post("", summary="创建简历")
async def create_resume(
    data: ResumeCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    创建新简历
    """
    # 检查文件哈希是否已存在
    existing = await resume_crud.get_by_hash(db, data.file_hash)
    if existing:
        raise ConflictException("简历已存在（文件重复）")
    
    resume = await resume_crud.create_resume(db, obj_in=data)
    return success_response(
        data=ResumeResponse.model_validate(resume).model_dump(),
        message="简历创建成功"
    )


@router.get("/check-hash", summary="检查文件哈希")
async def check_hash(
    file_hash: str = Query(..., description="文件哈希值"),
    db: AsyncSession = Depends(get_db),
):
    """
    检查文件哈希是否已存在（去重用）
    """
    exists = await resume_crud.check_hash_exists(db, file_hash)
    return success_response(data={"exists": exists})


@router.get("/{resume_id}", summary="获取简历详情")
async def get_resume(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    根据 ID 获取简历详情
    """
    resume = await resume_crud.get_with_applications(db, resume_id)
    if not resume:
        raise NotFoundException(f"简历不存在: {resume_id}")
    
    response = ResumeResponse.model_validate(resume)
    response.application_count = len(resume.applications) if resume.applications else 0
    
    return success_response(data=response.model_dump())


@router.patch("/{resume_id}", summary="更新简历")
async def update_resume(
    resume_id: str,
    data: ResumeUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    更新简历信息
    """
    resume = await resume_crud.get(db, resume_id)
    if not resume:
        raise NotFoundException(f"简历不存在: {resume_id}")
    
    resume = await resume_crud.update_resume(db, db_obj=resume, obj_in=data)
    return success_response(
        data=ResumeResponse.model_validate(resume).model_dump(),
        message="简历更新成功"
    )


@router.delete("/{resume_id}", summary="删除简历")
async def delete_resume(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    删除简历（同时删除关联的申请）
    """
    resume = await resume_crud.get(db, resume_id)
    if not resume:
        raise NotFoundException(f"简历不存在: {resume_id}")
    
    await resume_crud.delete(db, id=resume_id)
    return success_response(message="简历删除成功")


# ========== 批量操作 ==========

class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    resume_ids: List[str] = Field(..., min_length=1, description="简历ID列表")


class CheckHashesRequest(BaseModel):
    """批量哈希检查请求"""
    hashes: List[str] = Field(..., min_length=1, description="哈希值列表")


@router.post("/batch-delete", summary="批量删除简历")
async def batch_delete_resumes(
    data: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    批量删除简历
    """
    deleted_count = await resume_crud.delete_batch(db, data.resume_ids)
    return success_response(
        data={
            "deleted_count": deleted_count,
            "requested_count": len(data.resume_ids)
        },
        message=f"成功删除 {deleted_count} 份简历"
    )


@router.post("/check-hashes", summary="批量检查哈希")
async def check_hashes(
    data: CheckHashesRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    批量检查文件哈希是否已存在（去重用）
    """
    exists_map = await resume_crud.check_hashes_batch(db, data.hashes)
    existing_count = sum(1 for v in exists_map.values() if v)
    return success_response(
        data={
            "exists": exists_map,
            "existing_count": existing_count
        }
    )
