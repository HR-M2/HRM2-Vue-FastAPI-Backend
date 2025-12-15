"""
统一响应模块

定义标准 API 响应格式
"""
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    """
    统一响应模型
    
    示例:
        {
            "success": true,
            "code": 200,
            "message": "操作成功",
            "data": {...}
        }
    """
    success: bool = True
    code: int = 200
    message: str = "操作成功"
    data: Optional[T] = None


class PagedData(BaseModel, Generic[T]):
    """分页数据模型"""
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int  # 总页数


def success_response(
    data: Any = None,
    message: str = "操作成功",
    code: int = 200
) -> dict:
    """成功响应"""
    return {
        "success": True,
        "code": code,
        "message": message,
        "data": data
    }


def error_response(
    message: str = "操作失败",
    code: int = 400,
    data: Any = None
) -> dict:
    """错误响应"""
    return {
        "success": False,
        "code": code,
        "message": message,
        "data": data
    }


def paged_response(
    items: list,
    total: int,
    page: int,
    page_size: int,
    message: str = "查询成功"
) -> dict:
    """分页响应"""
    pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    return success_response(
        data={
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages
        },
        message=message
    )
