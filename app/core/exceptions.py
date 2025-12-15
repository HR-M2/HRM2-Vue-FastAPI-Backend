"""
异常处理模块

定义业务异常和全局异常处理器
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger

from .response import error_response


class AppException(Exception):
    """应用基础异常"""
    
    def __init__(
        self,
        message: str = "服务器内部错误",
        code: int = 500,
        data: dict = None
    ):
        self.message = message
        self.code = code
        self.data = data
        super().__init__(self.message)


class NotFoundException(AppException):
    """资源不存在异常"""
    
    def __init__(self, message: str = "资源不存在"):
        super().__init__(message=message, code=404)


class BadRequestException(AppException):
    """请求参数错误异常"""
    
    def __init__(self, message: str = "请求参数错误"):
        super().__init__(message=message, code=400)


class ConflictException(AppException):
    """资源冲突异常"""
    
    def __init__(self, message: str = "资源已存在"):
        super().__init__(message=message, code=409)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """应用异常处理器"""
    logger.warning(f"AppException: {exc.message} | Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.code,
        content=error_response(message=exc.message, code=exc.code, data=exc.data)
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP 异常处理器"""
    logger.warning(f"HTTPException: {exc.detail} | Path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(message=str(exc.detail), code=exc.status_code)
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """请求验证异常处理器"""
    errors = exc.errors()
    error_messages = []
    for error in errors:
        loc = " -> ".join(str(l) for l in error["loc"])
        error_messages.append(f"{loc}: {error['msg']}")
    
    message = "; ".join(error_messages)
    logger.warning(f"ValidationError: {message} | Path: {request.url.path}")
    
    return JSONResponse(
        status_code=422,
        content=error_response(
            message="请求参数验证失败",
            code=422,
            data={"errors": errors}
        )
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """通用异常处理器"""
    logger.exception(f"Unhandled Exception: {exc} | Path: {request.url.path}")
    return JSONResponse(
        status_code=500,
        content=error_response(message="服务器内部错误", code=500)
    )
