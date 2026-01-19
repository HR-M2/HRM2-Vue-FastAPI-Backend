"""
沉浸式面试模型模块
"""
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Text, ForeignKey, JSON, Boolean, Float, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from .base import BaseModel

if TYPE_CHECKING:
    from .application import Application
    from .psychological import PsychologicalReport


class ImmersiveSession(BaseModel):
    """
    沉浸式面试会话模型
    
    存储双摄像头面试、说话人识别、实时状态分析等数据
    
    speaker_segments JSON 格式示例:
    [
        {
            "speaker": "candidate",
            "start_time": 10.5,
            "end_time": 25.3,
            "duration": 14.8,
            "text": "该时间段的完整转录内容",
            "confidence": 0.92,
            "big_five_personality": {
                "openness": 0.75,
                "conscientiousness": 0.82,
                "extraversion": 0.68,
                "agreeableness": 0.71,
                "neuroticism": 0.35
            },
            "depression_risk": {
                "score": 15.2,
                "level": "low",
                "confidence": 0.88
            },
            "speech_features": {
                "pace": "normal",
                "volume": 0.7,
                "pitch_variance": 0.6,
                "pause_frequency": 0.3,
                "clarity": 0.9
            }
        }
    ]
    
    state_history JSON 格式示例:
    [
        {
            "timestamp": "2024-01-01T10:00:00Z",
            "segment_id": "seg_001",
            "emotion": {
                "emotion": "confident",
                "confidence": 0.85,
                "valence": 0.6,
                "arousal": 0.4
            },
            "engagement": 0.8,
            "nervousness": 0.2,
            "confidence_level": 0.75,
            "eye_contact": 0.9,
            "posture_score": 0.85,
            "cumulative_big_five": {
                "openness": 0.73,
                "conscientiousness": 0.79,
                "extraversion": 0.65,
                "agreeableness": 0.68,
                "neuroticism": 0.38
            },
            "cumulative_depression_risk": {
                "score": 18.5,
                "trend": "stable"
            }
        }
    ]
    """
    __tablename__ = "immersive_sessions"
    __table_args__ = (
        UniqueConstraint('application_id', name='uq_immersive_session_application'),
    )
    
    # ========== 外键关联 ==========
    application_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="应聘申请ID"
    )
    
    # ========== 会话配置 ==========
    local_camera_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="本地摄像头是否启用"
    )
    stream_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="远程推流URL"
    )
    config: Mapped[Optional[dict]] = mapped_column(
        JSON,
        default=dict,
        comment="面试配置参数"
    )
    
    # ========== 会话状态 ==========
    is_recording: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="是否正在录制"
    )
    is_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
        comment="是否已完成面试"
    )
    start_time: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="面试开始时间"
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="面试结束时间"
    )
    duration_seconds: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="面试总时长（秒）"
    )
    
    # ========== 实时数据 ==========
    transcripts: Mapped[Optional[list]] = mapped_column(
        JSON,
        default=list,
        comment="实时转录数据列表"
    )
    speaker_segments: Mapped[Optional[list]] = mapped_column(
        JSON,
        default=list,
        comment="说话人分段数据（包含心理分析）"
    )
    state_history: Mapped[Optional[list]] = mapped_column(
        JSON,
        default=list,
        comment="候选人状态分析历史"
    )
    
    # ========== 统计分析 ==========
    interviewer_speak_ratio: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="面试官说话时间占比"
    )
    candidate_speak_ratio: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="候选人说话时间占比"
    )
    total_questions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="总问题数量"
    )
    avg_response_time: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="平均回答时间（秒）"
    )
    avg_engagement: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="平均参与度"
    )
    avg_confidence: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="平均自信程度"
    )
    avg_nervousness: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="平均紧张程度"
    )
    
    # ========== 心理分析结果 ==========
    final_big_five: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="大五人格最终评估"
    )
    depression_assessment: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="抑郁风险评估"
    )
    psychological_wellness_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="综合心理健康评分 (0-100)"
    )
    
    # ========== 最终分析 ==========
    final_analysis: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="综合面试分析报告"
    )
    analysis_markdown: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Markdown格式的详细分析报告"
    )
    
    # ========== 技术元数据 ==========
    video_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="视频技术参数"
    )
    audio_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="音频技术参数"
    )
    
    # ========== 隐私和伦理 ==========
    sensitive_data_flags: Mapped[Optional[dict]] = mapped_column(
        JSON,
        default=dict,
        comment="敏感数据标记和处理规则"
    )
    
    # ========== 关联关系 ==========
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="immersive_session"
    )
    psychological_report: Mapped[Optional["PsychologicalReport"]] = relationship(
        "PsychologicalReport",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    @property
    def transcript_count(self) -> int:
        """转录记录数量"""
        return len(self.transcripts) if self.transcripts else 0
    
    @property
    def segment_count(self) -> int:
        """说话人分段数量"""
        return len(self.speaker_segments) if self.speaker_segments else 0
    
    @property
    def candidate_segments_count(self) -> int:
        """候选人说话分段数量"""
        if not self.speaker_segments:
            return 0
        return len([s for s in self.speaker_segments if s.get("speaker") == "candidate"])
    
    @property
    def has_psychological_analysis(self) -> bool:
        """是否包含心理分析数据"""
        return bool(self.final_big_five or self.depression_assessment)
    
    @property
    def has_final_report(self) -> bool:
        """是否有最终报告"""
        if not self.analysis_markdown:
            return False
        placeholder_markers = ["待 AI 服务生成", "分析报告占位"]
        return not any(marker in self.analysis_markdown for marker in placeholder_markers)
    
    @property
    def session_quality_score(self) -> float:
        """会话质量评分"""
        if not self.is_completed or self.duration_seconds < 60:
            return 0.0
        
        quality_factors = []
        
        # 时长合理性 (5-60分钟为最佳)
        if 300 <= self.duration_seconds <= 3600:  # 5-60分钟
            quality_factors.append(1.0)
        elif self.duration_seconds < 300:
            quality_factors.append(self.duration_seconds / 300)
        else:
            quality_factors.append(max(0.5, 3600 / self.duration_seconds))
        
        # 对话平衡性
        if 0.3 <= self.candidate_speak_ratio <= 0.7:
            quality_factors.append(1.0)
        else:
            balance_score = 1 - abs(0.5 - self.candidate_speak_ratio) * 2
            quality_factors.append(max(0.2, balance_score))
        
        # 数据完整性
        data_completeness = 0
        if self.transcript_count > 0:
            data_completeness += 0.3
        if self.segment_count > 0:
            data_completeness += 0.3
        if self.has_psychological_analysis:
            data_completeness += 0.4
        quality_factors.append(data_completeness)
        
        return sum(quality_factors) / len(quality_factors) * 100
    
    def get_latest_psychological_state(self) -> Optional[dict]:
        """获取最新的心理状态"""
        if not self.state_history:
            return None
        return max(self.state_history, key=lambda x: x.get("timestamp", ""))
    
    def get_depression_risk_trend(self) -> str:
        """获取抑郁风险趋势"""
        if not self.state_history or len(self.state_history) < 2:
            return "insufficient_data"
        
        recent_scores = []
        for state in self.state_history[-5:]:  # 最近5个状态点
            risk_data = state.get("cumulative_depression_risk", {})
            if "score" in risk_data:
                recent_scores.append(risk_data["score"])
        
        if len(recent_scores) < 2:
            return "insufficient_data"
        
        # 简单趋势分析
        if recent_scores[-1] > recent_scores[0] + 5:
            return "increasing"
        elif recent_scores[-1] < recent_scores[0] - 5:
            return "decreasing"
        else:
            return "stable"
    
    def __repr__(self) -> str:
        return f"<ImmersiveSession(id={self.id}, duration={self.duration_seconds}s, segments={self.segment_count})>"