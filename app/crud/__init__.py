"""
CRUD 模块 - SQLModel 简化版

移除了薄包装方法，保留有价值的业务查询
"""
from .base import CRUDBase
from .position import position_crud
from .resume import resume_crud
from .application import application_crud
from .screening import screening_crud
from .video import video_crud
from .interview import interview_crud
from .analysis import analysis_crud
from .experience import experience_crud

__all__ = [
    "CRUDBase",
    "position_crud",
    "resume_crud", 
    "application_crud",
    "screening_crud",
    "video_crud",
    "interview_crud",
    "analysis_crud",
    "experience_crud",
]

