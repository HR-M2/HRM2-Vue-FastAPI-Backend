"""
SQLModel 模型模块

使用 SQLModel 统一 ORM Model 和 Pydantic Schema
"""
from .base import SQLModelBase, TimestampMixin
from .position import Position, PositionCreate, PositionUpdate, PositionResponse, PositionListResponse
from .resume import Resume, ResumeCreate, ResumeUpdate, ResumeResponse, ResumeListResponse
from .application import (
    Application, ApplicationCreate, ApplicationUpdate, 
    ApplicationResponse, ApplicationListResponse, ApplicationDetailResponse,
    ScreeningTaskBrief, VideoAnalysisBrief, InterviewSessionBrief, ComprehensiveAnalysisBrief
)
from .screening import ScreeningTask, ScreeningTaskCreate, ScreeningResultUpdate, ScreeningTaskResponse, TaskStatus, ScreeningScore, AppliedExperienceItem
from .video import VideoAnalysis, VideoAnalysisCreate, VideoResultUpdate, VideoAnalysisResponse, BigFiveScores
from .interview import InterviewSession, InterviewSessionCreate, InterviewSessionUpdate, InterviewSessionResponse, QAMessage, QAMessageCreate, MessagesSyncRequest, GenerateQuestionsRequest
from .analysis import ComprehensiveAnalysis, ComprehensiveAnalysisCreate, ComprehensiveAnalysisUpdate, ComprehensiveAnalysisResponse, RecommendationLevel, DimensionScoreItem
from .experience import AgentExperience, AgentExperienceCreate, AgentExperienceResponse, ExperienceCategory, FeedbackRequest, FeedbackResponse

__all__ = [
    # Base
    "SQLModelBase",
    "TimestampMixin",
    # Position
    "Position",
    "PositionCreate",
    "PositionUpdate", 
    "PositionResponse",
    "PositionListResponse",
    # Resume
    "Resume",
    "ResumeCreate",
    "ResumeUpdate",
    "ResumeResponse",
    "ResumeListResponse",
    # Application
    "Application",
    "ApplicationCreate",
    "ApplicationUpdate",
    "ApplicationResponse",
    "ApplicationListResponse",
    "ApplicationDetailResponse",
    "ScreeningTaskBrief",
    "VideoAnalysisBrief",
    "InterviewSessionBrief",
    "ComprehensiveAnalysisBrief",
    # Screening
    "ScreeningTask",
    "ScreeningTaskCreate",
    "ScreeningResultUpdate",
    "ScreeningTaskResponse",
    "ScreeningScore",
    "TaskStatus",
    "AppliedExperienceItem",
    # Video
    "VideoAnalysis",
    "VideoAnalysisCreate",
    "VideoResultUpdate",
    "VideoAnalysisResponse",
    "BigFiveScores",
    # Interview
    "InterviewSession",
    "InterviewSessionCreate",
    "InterviewSessionUpdate",
    "InterviewSessionResponse",
    "QAMessage",
    "QAMessageCreate",
    "MessagesSyncRequest",
    "GenerateQuestionsRequest",
    # Analysis
    "ComprehensiveAnalysis",
    "ComprehensiveAnalysisCreate",
    "ComprehensiveAnalysisUpdate",
    "ComprehensiveAnalysisResponse",
    "RecommendationLevel",
    "DimensionScoreItem",
    # Experience
    "AgentExperience",
    "AgentExperienceCreate",
    "AgentExperienceResponse",
    "ExperienceCategory",
    "FeedbackRequest",
    "FeedbackResponse",
]
