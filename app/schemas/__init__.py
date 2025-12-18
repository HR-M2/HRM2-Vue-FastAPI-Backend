"""
Pydantic Schemas 模块

定义 API 请求/响应的数据验证模型
"""
from .base import BaseSchema, TimestampSchema
from .position import (
    PositionCreate,
    PositionUpdate,
    PositionResponse,
    PositionListResponse,
)
from .resume import (
    ResumeCreate,
    ResumeUpdate,
    ResumeResponse,
    ResumeListResponse,
)
from .application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
    ApplicationListResponse,
    ApplicationDetailResponse,
)
from .screening import (
    ScreeningTaskCreate,
    ScreeningTaskResponse,
    ScreeningResultUpdate,
)
from .video import (
    VideoAnalysisCreate,
    VideoAnalysisResponse,
    VideoResultUpdate,
)
from .interview import (
    InterviewSessionCreate,
    InterviewSessionResponse,
    QAMessageCreate,
    GenerateQuestionsRequest,
)
from .analysis import (
    ComprehensiveAnalysisCreate,
    ComprehensiveAnalysisResponse,
)
from .immersive import (
    ImmersiveSessionCreate,
    ImmersiveSessionResponse,
    ImmersiveSessionUpdate,
    SpeakerDiarizationRequest,
    SpeakerDiarizationResponse,
    StateAnalysisRequest,
    StateAnalysisResponse,
    CandidateState,
    QuestionSuggestion,
    InterviewInsight,
)

__all__ = [
    # Base
    "BaseSchema",
    "TimestampSchema",
    # Position
    "PositionCreate",
    "PositionUpdate",
    "PositionResponse",
    "PositionListResponse",
    # Resume
    "ResumeCreate",
    "ResumeUpdate",
    "ResumeResponse",
    "ResumeListResponse",
    # Application
    "ApplicationCreate",
    "ApplicationUpdate",
    "ApplicationResponse",
    "ApplicationListResponse",
    "ApplicationDetailResponse",
    # Screening
    "ScreeningTaskCreate",
    "ScreeningTaskResponse",
    "ScreeningResultUpdate",
    # Video
    "VideoAnalysisCreate",
    "VideoAnalysisResponse",
    "VideoResultUpdate",
    # Interview
    "InterviewSessionCreate",
    "InterviewSessionResponse",
    "QAMessageCreate",
    "GenerateQuestionsRequest",
    # Analysis
    "ComprehensiveAnalysisCreate",
    "ComprehensiveAnalysisResponse",
    # Immersive
    "ImmersiveSessionCreate",
    "ImmersiveSessionResponse",
    "ImmersiveSessionUpdate",
    "SpeakerDiarizationRequest",
    "SpeakerDiarizationResponse",
    "StateAnalysisRequest",
    "StateAnalysisResponse",
    "CandidateState",
    "QuestionSuggestion",
    "InterviewInsight",
]
