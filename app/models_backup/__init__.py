"""
数据库模型模块

模型关系:
    Position (岗位)
        |
        | 1:N
        v
    Application (应聘申请) <-- 核心表
        |
        | N:1
        |
    Resume (简历)

    Application (应聘申请)
        |
        +-- 1:N --> ScreeningTask (筛选任务)
        |
        +-- 1:N --> VideoAnalysis (视频分析)
        |
        +-- 1:N --> InterviewSession (面试会话)
        |
        +-- 1:N --> ComprehensiveAnalysis (综合分析)
"""
from .base import BaseModel, TimestampMixin
from .position import Position
from .resume import Resume
from .application import Application
from .screening import ScreeningTask
from .video import VideoAnalysis
from .interview import InterviewSession
from .analysis import ComprehensiveAnalysis

__all__ = [
    "BaseModel",
    "TimestampMixin",
    "Position",
    "Resume",
    "Application",
    "ScreeningTask",
    "VideoAnalysis",
    "InterviewSession",
    "ComprehensiveAnalysis",
]
