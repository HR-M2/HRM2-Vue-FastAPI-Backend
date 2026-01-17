"""
沉浸式面试相关 Schema
"""
from typing import Optional, List, Dict, Literal
from datetime import datetime
from pydantic import Field

from .base import BaseSchema, TimestampSchema


class BigFivePersonality(BaseSchema):
    """大五人格分析"""
    
    openness: float = Field(..., ge=0, le=1, description="开放性")
    conscientiousness: float = Field(..., ge=0, le=1, description="尽责性")
    extraversion: float = Field(..., ge=0, le=1, description="外向性")
    agreeableness: float = Field(..., ge=0, le=1, description="宜人性")
    neuroticism: float = Field(..., ge=0, le=1, description="神经质")


class DepressionRisk(BaseSchema):
    """抑郁风险评估"""
    
    score: float = Field(..., ge=0, le=100, description="抑郁可能性评分")
    level: Literal["low", "medium", "high"] = Field(..., description="风险等级")
    confidence: float = Field(..., ge=0, le=1, description="分析置信度")


class SpeechFeatures(BaseSchema):
    """语音特征分析"""
    
    pace: Literal["slow", "normal", "fast"] = Field("normal", description="语速")
    volume: float = Field(0, ge=0, le=1, description="音量")
    pitch_variance: float = Field(0, ge=0, le=1, description="音调变化")
    pause_frequency: float = Field(0, ge=0, le=1, description="停顿频率")
    clarity: float = Field(0, ge=0, le=1, description="清晰度")


class SpeakerSegment(BaseSchema):
    """说话人片段"""
    
    speaker: Literal["interviewer", "candidate"] = Field(..., description="说话人")
    start_time: float = Field(..., description="开始时间（秒）")
    end_time: float = Field(..., description="结束时间（秒）")
    duration: float = Field(0, description="时长（秒）")
    text: str = Field("", description="转录文本")
    confidence: float = Field(0.0, ge=0, le=1, description="置信度")
    
    # 心理分析数据（仅候选人）
    big_five_personality: Optional[BigFivePersonality] = Field(None, description="大五人格分析")
    depression_risk: Optional[DepressionRisk] = Field(None, description="抑郁风险评估")
    speech_features: Optional[SpeechFeatures] = Field(None, description="语音特征分析")


class EmotionState(BaseSchema):
    """情绪状态"""
    
    emotion: str = Field(..., description="主要情绪")
    confidence: float = Field(..., ge=0, le=1, description="置信度")
    valence: float = Field(0, ge=-1, le=1, description="效价（正负情绪）")
    arousal: float = Field(0, ge=0, le=1, description="唤醒度")


class CandidateState(BaseSchema):
    """候选人状态分析"""
    
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    segment_id: Optional[str] = Field(None, description="关联的说话人分段ID")
    emotion: EmotionState = Field(..., description="情绪状态")
    engagement: float = Field(0, ge=0, le=1, description="参与度")
    nervousness: float = Field(0, ge=0, le=1, description="紧张程度")
    confidence_level: float = Field(0, ge=0, le=1, description="自信程度")
    eye_contact: float = Field(0, ge=0, le=1, description="眼神接触度")
    posture_score: float = Field(0, ge=0, le=1, description="姿态评分")
    speech_clarity: float = Field(0, ge=0, le=1, description="语言清晰度")
    speech_pace: Literal["slow", "normal", "fast"] = Field("normal", description="语速")
    
    # 累积心理分析
    cumulative_big_five: Optional[BigFivePersonality] = Field(None, description="累积大五人格")
    cumulative_depression_risk: Optional[Dict] = Field(None, description="累积抑郁风险")


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


# ========== 新增的 Schema ==========

class TranscriptCreate(BaseSchema):
    """创建转录记录"""
    
    speaker: Literal["interviewer", "candidate", "unknown"] = Field(..., description="说话人")
    text: str = Field(..., min_length=1, description="转录文本")
    is_final: bool = Field(False, description="是否为最终结果")


class SpeakerSegmentCreate(BaseSchema):
    """创建说话人分段"""
    
    speaker: Literal["interviewer", "candidate"] = Field(..., description="说话人")
    start_time: float = Field(..., ge=0, description="开始时间（秒）")
    end_time: float = Field(..., gt=0, description="结束时间（秒）")
    text: str = Field("", description="转录文本")
    confidence: float = Field(0.0, ge=0, le=1, description="置信度")
    
    # 可选的心理分析数据
    big_five_personality: Optional[BigFivePersonality] = None
    depression_risk: Optional[DepressionRisk] = None
    speech_features: Optional[SpeechFeatures] = None


class StateRecordCreate(BaseSchema):
    """创建状态记录"""
    
    segment_id: Optional[str] = Field(None, description="关联的说话人分段ID")
    emotion: EmotionState = Field(..., description="情绪状态")
    engagement: float = Field(..., ge=0, le=1, description="参与度")
    nervousness: float = Field(..., ge=0, le=1, description="紧张程度")
    confidence_level: float = Field(..., ge=0, le=1, description="自信程度")
    eye_contact: float = Field(..., ge=0, le=1, description="眼神接触度")
    posture_score: float = Field(..., ge=0, le=1, description="姿态评分")
    speech_clarity: float = Field(..., ge=0, le=1, description="语言清晰度")
    speech_pace: Literal["slow", "normal", "fast"] = Field("normal", description="语速")


class SyncDataRequest(BaseSchema):
    """同步实时数据请求"""
    
    transcripts: Optional[List[TranscriptCreate]] = Field(None, description="转录数据列表")
    speaker_segments: Optional[List[SpeakerSegmentCreate]] = Field(None, description="说话人分段列表")
    state_records: Optional[List[StateRecordCreate]] = Field(None, description="状态记录列表")


class SessionStatistics(BaseSchema):
    """会话统计数据"""
    
    total_segments: int = Field(0, description="总分段数")
    candidate_segments: int = Field(0, description="候选人分段数")
    interviewer_segments: int = Field(0, description="面试官分段数")
    candidate_speak_ratio: float = Field(0, description="候选人说话时间占比")
    interviewer_speak_ratio: float = Field(0, description="面试官说话时间占比")
    avg_engagement: float = Field(0, description="平均参与度")
    avg_confidence: float = Field(0, description="平均自信程度")
    avg_nervousness: float = Field(0, description="平均紧张程度")
    session_quality_score: float = Field(0, description="会话质量评分")


class PsychologicalSummary(BaseSchema):
    """心理分析汇总"""
    
    final_big_five: Optional[Dict] = Field(None, description="最终大五人格评估")
    depression_assessment: Optional[Dict] = Field(None, description="抑郁风险评估")
    psychological_wellness_score: float = Field(0, description="综合心理健康评分")
    trend_analysis: Optional[Dict] = Field(None, description="趋势分析")


class ImmersiveSessionDetailResponse(ImmersiveSessionResponse):
    """完整的沉浸式面试会话响应（含汇总数据）"""
    
    # 统计汇总
    statistics: Optional[SessionStatistics] = Field(None, description="统计数据")
    
    # 心理分析汇总  
    psychological_summary: Optional[PsychologicalSummary] = Field(None, description="心理分析汇总")
    
    # 完整数据（仅在完成后返回）
    full_transcripts: Optional[List[RealtimeTranscript]] = Field(None, description="完整转录记录")
    full_speaker_segments: Optional[List[SpeakerSegment]] = Field(None, description="完整说话人分段")
    full_state_history: Optional[List[CandidateState]] = Field(None, description="完整状态历史")
