"""
API 路由模块
"""
from fastapi import APIRouter

from .v1 import positions, resumes, applications, screening, video, interview, analysis

# 创建主路由
api_router = APIRouter()

# 注册各模块路由
api_router.include_router(
    positions.router,
    prefix="/positions",
    tags=["岗位管理"]
)
api_router.include_router(
    resumes.router,
    prefix="/resumes",
    tags=["简历管理"]
)
api_router.include_router(
    applications.router,
    prefix="/applications",
    tags=["应聘申请"]
)
api_router.include_router(
    screening.router,
    prefix="/screening",
    tags=["简历筛选"]
)
api_router.include_router(
    video.router,
    prefix="/video",
    tags=["视频分析"]
)
api_router.include_router(
    interview.router,
    prefix="/interview",
    tags=["面试辅助"]
)
api_router.include_router(
    analysis.router,
    prefix="/analysis",
    tags=["综合分析"]
)
