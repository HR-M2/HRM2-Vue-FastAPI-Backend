"""
沉浸式面试相关 Schema
"""
from typing import Optional, List, Dict, Literal
from datetime import datetime
from pydantic import Field

from .base import BaseSchema, TimestampSchema


class SpeakerSegment(BaseSchema):
    """说话人片段"""
    
    speaker: Literal["interviewer", "candidate"] = Field(..., description="说话人")
    start_time: float = Field(..., description="开始时间（秒）")
    end_time: float = Field(..., description="结束时间（秒）")
    text: str = Field("", description="转录文本")
    confidence: float = Field(0.0, ge=0, le=1, description="置信度")


class EmotionState(BaseSchema):
    """情绪状态"""
    
    emotion: str = Field(..., description="主要情绪")
    confidence: float = Field(..., ge=0, le=1, description="置信度")
    valence: float = Field(0, ge=-1, le=1, description="效价（正负情绪）")
    arousal: float = Field(0, ge=0, le=1, description="唤醒度")


class CandidateState(BaseSchema):
    """候选人状态分析"""
    
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    emotion: EmotionState = Field(..., description="情绪状态")
    engagement: float = Field(0, ge=0, le=1, description="参与度")
    nervousness: float = Field(0, ge=0, le=1, description="紧张程度")
    confidence_level: float = Field(0, ge=0, le=1, description="自信程度")
    eye_contact: float = Field(0, ge=0, le=1, description="眼神接触度")
    posture_score: float = Field(0, ge=0, le=1, description="姿态评分")
    speech_clarity: float = Field(0, ge=0, le=1, description="语言清晰度")
    speech_pace: Literal["slow", "normal", "fast"] = Field("normal", description="语速")


class ImmersiveSessionCreate(BaseSchema):
    """创建沉浸式面试会话"""
    
    application_id: str = Field(..., description="应聘申请ID")
    local_camera_enabled: bool = Field(True, description="本地摄像头启用")
    stream_url: Optional[str] = Field(None, description="远程推流URL")
    config: Optional[Dict] = Field(default_factory=dict, description="会话配置")


class ImmersiveSessionUpdate(BaseSchema):
    """更新沉浸式面试会话"""
    
    stream_url: Optional[str] = None
    is_recording: Optional[bool] = None
    is_completed: Optional[bool] = None
    final_analysis: Optional[Dict] = None


class SpeakerDiarizationRequest(BaseSchema):
    """说话人识别请求"""
    
    audio_data: Optional[str] = Field(None, description="Base64编码的音频数据")
    audio_url: Optional[str] = Field(None, description="音频URL")
    duration: float = Field(..., description="音频时长（秒）")


class SpeakerDiarizationResponse(BaseSchema):
    """说话人识别响应"""
    
    segments: List[SpeakerSegment] = Field(default_factory=list, description="说话人片段")
    total_interviewer_time: float = Field(0, description="面试官总说话时长")
    total_candidate_time: float = Field(0, description="候选人总说话时长")


class StateAnalysisRequest(BaseSchema):
    """状态分析请求"""
    
    frame_data: Optional[str] = Field(None, description="Base64编码的视频帧")
    audio_segment: Optional[str] = Field(None, description="Base64编码的音频片段")
    context: Optional[Dict] = Field(None, description="上下文信息")


class StateAnalysisResponse(BaseSchema):
    """状态分析响应"""
    
    state: CandidateState = Field(..., description="候选人状态")
    suggestions: List[str] = Field(default_factory=list, description="面试建议")
    alerts: List[str] = Field(default_factory=list, description="提醒信息")


class RealtimeTranscript(BaseSchema):
    """实时转录文本"""
    
    speaker: Literal["interviewer", "candidate", "unknown"] = Field(..., description="说话人")
    text: str = Field(..., description="转录文本")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    is_final: bool = Field(False, description="是否为最终结果")


class ImmersiveSessionResponse(TimestampSchema):
    """沉浸式面试会话响应"""
    
    application_id: str
    local_camera_enabled: bool
    stream_url: Optional[str]
    config: Dict
    is_recording: bool = False
    is_completed: bool = False
    
    # 实时数据
    transcripts: List[RealtimeTranscript] = Field(default_factory=list)
    speaker_segments: List[SpeakerSegment] = Field(default_factory=list)
    state_history: List[CandidateState] = Field(default_factory=list)
    
    # 统计
    duration_seconds: float = 0
    interviewer_speak_ratio: float = 0
    candidate_speak_ratio: float = 0
    
    # 最终分析
    final_analysis: Optional[Dict] = None
    
    # 关联信息
    candidate_name: Optional[str] = None
    position_title: Optional[str] = None


class QuestionSuggestion(BaseSchema):
    """问题建议"""
    
    question: str = Field(..., description="建议问题")
    type: Literal["followup", "alternative", "probe"] = Field(..., description="问题类型")
    priority: int = Field(1, ge=1, le=10, description="优先级")
    reason: Optional[str] = Field(None, description="建议原因")


class InterviewInsight(BaseSchema):
    """面试洞察"""
    
    category: str = Field(..., description="洞察类别")
    content: str = Field(..., description="洞察内容")
    severity: Literal["info", "warning", "alert"] = Field("info", description="严重程度")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
