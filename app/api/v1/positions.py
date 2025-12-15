"""
岗位管理 API 路由
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
)
from app.core.exceptions import NotFoundException, ConflictException
from app.crud import position_crud
from app.schemas.position import (
    PositionCreate,
    PositionUpdate,
    PositionResponse,
    PositionListResponse,
)

router = APIRouter()


@router.get("", summary="获取岗位列表", response_model=PagedResponseModel[PositionListResponse])
async def get_positions(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    is_active: Optional[bool] = Query(None, description="是否启用"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取岗位列表，支持分页和状态筛选
    """
    skip = (page - 1) * page_size
    
    if is_active is True:
        positions = await position_crud.get_active_positions(
            db, skip=skip, limit=page_size
        )
        total = await position_crud.count_active(db)
    else:
        positions = await position_crud.get_multi(
            db, skip=skip, limit=page_size
        )
        total = await position_crud.count(db)
    
    items = []
    for p in positions:
        item = PositionListResponse.model_validate(p)
        item.application_count = len(p.applications) if p.applications else 0
        items.append(item.model_dump())
    
    return paged_response(items, total, page, page_size)


@router.post("", summary="创建岗位", response_model=ResponseModel[PositionResponse])
async def create_position(
    data: PositionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    创建新岗位
    """
    # 检查岗位名称是否已存在
    existing = await position_crud.get_by_title(db, data.title)
    if existing:
        raise ConflictException(f"岗位 '{data.title}' 已存在")
    
    position = await position_crud.create_position(db, obj_in=data)
    return success_response(
        data=PositionResponse.model_validate(position).model_dump(),
        message="岗位创建成功"
    )


@router.get("/{position_id}", summary="获取岗位详情", response_model=ResponseModel[PositionResponse])
async def get_position(
    position_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    根据 ID 获取岗位详情
    """
    position = await position_crud.get_with_count(db, position_id)
    if not position:
        raise NotFoundException(f"岗位不存在: {position_id}")
    
    response = PositionResponse.model_validate(position)
    response.application_count = len(position.applications) if position.applications else 0
    
    return success_response(data=response.model_dump())


@router.patch("/{position_id}", summary="更新岗位", response_model=ResponseModel[PositionResponse])
async def update_position(
    position_id: str,
    data: PositionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    更新岗位信息
    """
    position = await position_crud.get(db, position_id)
    if not position:
        raise NotFoundException(f"岗位不存在: {position_id}")
    
    # 检查新名称是否冲突
    if data.title and data.title != position.title:
        existing = await position_crud.get_by_title(db, data.title)
        if existing:
            raise ConflictException(f"岗位 '{data.title}' 已存在")
    
    position = await position_crud.update_position(db, db_obj=position, obj_in=data)
    return success_response(
        data=PositionResponse.model_validate(position).model_dump(),
        message="岗位更新成功"
    )


@router.delete("/{position_id}", summary="删除岗位", response_model=MessageResponse)
async def delete_position(
    position_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    删除岗位（同时删除关联的申请）
    """
    position = await position_crud.get(db, position_id)
    if not position:
        raise NotFoundException(f"岗位不存在: {position_id}")
    
    await position_crud.delete(db, id=position_id)
    return success_response(message="岗位删除成功")
