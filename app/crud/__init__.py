"""
CRUD 操作模块
"""
from .position import position_crud
from .resume import resume_crud
from .application import application_crud
from .screening import screening_crud
from .video import video_crud
from .interview import interview_crud
from .analysis import analysis_crud

__all__ = [
    "position_crud",
    "resume_crud",
    "application_crud",
    "screening_crud",
    "video_crud",
    "interview_crud",
    "analysis_crud",
]
