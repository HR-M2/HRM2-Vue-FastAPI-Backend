"""
FastAPI 主应用入口

HRM2 企业招聘管理系统后端
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from loguru import logger

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.response import success_response, DictResponse
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
)
from app.api import api_router


def custom_generate_unique_id(route: APIRoute) -> str:
    """
    自定义 OpenAPI operationId 生成函数
    
    使用路由函数名作为 operationId，生成更简短的 API 名称
    """
    return route.name


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    启动时初始化数据库，关闭时释放连接
    """
    logger.info(f"启动应用: {settings.app_name}")
    logger.info(f"环境: {settings.app_env}")
    logger.info(f"调试模式: {settings.debug}")
    
    # 初始化数据库
    await init_db()
    logger.info("数据库初始化完成")
    
    yield
    
    # 关闭数据库连接
    await close_db()
    logger.info("应用已关闭")


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用实例
    """
    app = FastAPI(
        title=settings.app_name,
        description="HRM2 企业招聘管理系统 API",
        version="2.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
        generate_unique_id_function=custom_generate_unique_id,
    )
    
    # 注册异常处理器
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    # 注册路由
    app.include_router(api_router, prefix="/api/v1")
    
    # 健康检查
    @app.get("/health", tags=["系统"], response_model=DictResponse)
    async def health_check():
        """健康检查接口"""
        return success_response(data={"status": "healthy"})
    
    # 根路径
    @app.get("/", tags=["系统"], response_model=DictResponse)
    async def root():
        """API 根路径"""
        return success_response(data={
            "name": settings.app_name,
            "version": "2.0.0",
            "docs": "/docs" if settings.debug else None,
        })
    
    # 配置 CORS（必须放在最后添加，这样它会最先执行）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.debug,
    )
