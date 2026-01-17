"""
沉浸式面试AI助手服务

专门处理沉浸式面试的AI相关功能：
- 智能问题生成
- 心理状态分析
- 对话历史分析
- 面试洞察生成
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from .llm_client import get_llm_client

logger = logging.getLogger(__name__)


class ImmersiveInterviewAgent:
    """沉浸式面试AI助手"""
    
    def __init__(self):
        self._llm = get_llm_client()
    
    async def generate_question_suggestions(
        self,
        context: Dict[str, Any],
        count: int = 5,
        difficulty: str = "medium",
        focus_areas: Optional[List[str]] = None,
        question_type: str = "mixed"
    ) -> List[Dict[str, Any]]:
        """生成智能问题建议"""
        try:
            suggestions = await self._generate_ai_questions(
                count, difficulty, focus_areas, question_type, context
            )
            return suggestions
        except Exception as e:
            # 如果AI服务失败，回退到模拟数据
            logger.warning(f"AI问题生成失败，使用备用方案: {e}")
            return self._generate_mock_questions(
                count, difficulty, focus_areas, question_type, context
            )
    
    async def _generate_ai_questions(
        self,
        count: int,
        difficulty: str,
        focus_areas: Optional[List[str]],
        question_type: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """使用AI服务生成问题建议"""
        
        # 构建AI提示词
        system_prompt = """你是一位资深的面试官，专门负责沉浸式面试的问题建议。
你需要根据候选人的心理状态、对话历史和岗位要求，生成智能的面试问题建议。

沉浸式面试的特点：
- 实时监控候选人的心理状态（情绪、紧张程度、参与度等）
- 基于心理分析数据调整问题策略
- 考虑对话流程和话题连贯性
- 提供问题时机建议"""

        user_prompt = self._build_ai_question_prompt(
            count, difficulty, focus_areas, question_type, context
        )
        
        try:
            result = await self._llm.complete_json(system_prompt, user_prompt, temperature=0.7)
            
            suggestions = []
            for q in result.get('suggestions', [])[:count]:
                suggestion = {
                    "question": q.get("question", ""),
                    "type": q.get("type", "behavioral"),
                    "priority": q.get("priority", 5),
                    "reason": q.get("reason", ""),
                    "psychological_context": q.get("psychological_context", ""),
                    "timing_suggestion": q.get("timing_suggestion", "适合当前提问"),
                    "expected_response_indicators": q.get("expected_response_indicators", [
                        "技术深度", "表达清晰度", "情绪稳定性", "自信程度"
                    ])
                }
                suggestions.append(suggestion)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"AI问题生成失败: {e}")
            raise
    
    def _build_ai_question_prompt(
        self,
        count: int,
        difficulty: str,
        focus_areas: Optional[List[str]],
        question_type: str,
        context: Dict[str, Any]
    ) -> str:
        """构建AI问题生成的提示词"""
        
        # 心理状态分析
        psychological_context = context.get("psychological_context", {})
        psychological_desc = "暂无心理状态数据"
        if psychological_context:
            emotion = psychological_context.get("current_emotion", {}).get("emotion", "未知")
            engagement = psychological_context.get("engagement_level", 0)
            nervousness = psychological_context.get("nervousness_level", 0)
            confidence = psychological_context.get("confidence_level", 0)
            psychological_desc = f"当前情绪: {emotion}, 参与度: {engagement:.2f}, 紧张程度: {nervousness:.2f}, 自信程度: {confidence:.2f}"
        
        # 对话历史分析
        conversation_context = context.get("conversation_context", {})
        conversation_desc = "暂无对话历史"
        if conversation_context:
            recent_topics = conversation_context.get("recent_topics", [])
            last_response = conversation_context.get("last_candidate_response", "")
            flow_stage = conversation_context.get("conversation_flow", "opening")
            conversation_desc = f"最近话题: {', '.join(recent_topics) if recent_topics else '无'}, 对话阶段: {flow_stage}"
            if last_response:
                conversation_desc += f", 最后回答: {last_response[:100]}..."
        
        # 候选人和岗位信息
        candidate_info = context.get("candidate_info", {})
        position_info = context.get("position_info", {})
        
        prompt = f"""# 沉浸式面试问题生成请求

## 基本要求
- 生成问题数量: {count}
- 问题难度: {difficulty}
- 问题类型: {question_type}
- 关注领域: {', '.join(focus_areas) if focus_areas else '无特定要求'}

## 候选人信息
- 姓名: {candidate_info.get('name', '未知')}
- 简历摘要: {candidate_info.get('content', '未提供')[:200]}...

## 岗位信息
- 职位: {position_info.get('title', '未知')}
- 技能要求: {', '.join(position_info.get('required_skills', [])) if position_info.get('required_skills') else '未指定'}
- 职位描述: {position_info.get('description', '未提供')[:200]}...

## 心理状态分析
{psychological_desc}

## 对话历史分析
{conversation_desc}

## 问题生成策略

### 根据心理状态调整：
1. **高紧张程度 (>0.7)**: 使用缓解性问题，避免增加压力
2. **低参与度 (<0.5)**: 使用激发兴趣的问题，提高互动
3. **高自信程度 (>0.8)**: 可以提出挑战性问题，深入考察
4. **情绪不稳定**: 使用稳定性问题，观察情绪管理能力

### 根据对话阶段调整：
- **opening**: 轻松开场问题
- **warming_up**: 逐步深入的问题
- **deep_dive**: 核心技能考察问题
- **closing**: 总结性或开放性问题

### 问题类型说明：
- **technical**: 技术能力考察
- **behavioral**: 行为面试问题
- **situational**: 情景模拟问题
- **psychological**: 心理状态相关问题
- **mixed**: 混合类型

## JSON返回格式
{{
    "suggestions": [
        {{
            "question": "完整的问题内容",
            "type": "问题类型 (technical/behavioral/situational/psychological)",
            "priority": 1-10的优先级数字,
            "reason": "推荐这个问题的具体原因",
            "psychological_context": "基于心理状态的上下文说明",
            "timing_suggestion": "提问时机建议",
            "expected_response_indicators": ["预期回答指标1", "指标2", "指标3"]
        }}
    ]
}}

请根据以上信息生成{count}个高质量的面试问题建议，确保问题：
1. 符合候选人当前的心理状态
2. 与对话历史和话题流向连贯
3. 难度适中，能有效考察相关能力
4. 包含明确的提问时机建议

请直接返回JSON，不要包含其他内容。"""
        
        return prompt

    def _generate_mock_questions(
        self,
        count: int,
        difficulty: str,
        focus_areas: Optional[List[str]],
        question_type: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成模拟问题建议（AI服务失败时的备用方案）"""
        
        suggestions = []
        psychological_context = context.get("psychological_context", {})
        conversation_context = context.get("conversation_context", {})
        
        for i in range(count):
            # 根据心理状态调整问题类型
            if psychological_context.get("nervousness_level", 0) > 0.7:
                # 候选人紧张，建议缓解问题
                question = "我看你有点紧张，我们可以先聊聊你最熟悉的项目，放轻松一点"
                question_type_actual = "psychological"
                reason = "候选人紧张程度较高，建议使用缓解性问题"
                timing_suggestion = "立即提问，缓解紧张情绪"
            elif psychological_context.get("engagement_level", 0) < 0.5:
                # 参与度低，建议激发兴趣的问题
                question = "你最感兴趣的技术领域是什么？为什么？"
                question_type_actual = "behavioral"
                reason = "候选人参与度较低，建议使用激发兴趣的问题"
                timing_suggestion = "适合在对话间隙提问"
            else:
                # 正常状态，根据对话历史生成问题
                recent_topics = conversation_context.get("recent_topics", [])
                if "技术能力" in recent_topics:
                    question = f"刚才你提到了技术实现，能具体说说你是如何解决{difficulty}级别的技术挑战的？"
                    question_type_actual = "technical"
                    reason = "基于之前的技术讨论，深入了解技术能力"
                else:
                    question = f"请描述一个你认为最能体现你能力的项目（{difficulty}难度）"
                    question_type_actual = "behavioral"
                    reason = "了解候选人的核心能力和项目经验"
                timing_suggestion = "适合在当前话题结束后提问"
            
            suggestion = {
                "question": question,
                "type": question_type_actual,
                "priority": max(1, count - i),  # 优先级递减
                "reason": reason,
                "psychological_context": self._get_psychological_context_description(psychological_context),
                "timing_suggestion": timing_suggestion,
                "expected_response_indicators": [
                    "技术深度",
                    "表达清晰度", 
                    "情绪稳定性",
                    "自信程度"
                ]
            }
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def _get_psychological_context_description(self, psychological_context: Dict) -> str:
        """生成心理状态上下文描述"""
        if not psychological_context:
            return "暂无心理状态数据"
        
        emotion = psychological_context.get("current_emotion", {}).get("emotion", "未知")
        engagement = psychological_context.get("engagement_level", 0)
        nervousness = psychological_context.get("nervousness_level", 0)
        confidence = psychological_context.get("confidence_level", 0)
        
        return f"当前情绪: {emotion}, 参与度: {engagement:.2f}, 紧张程度: {nervousness:.2f}, 自信程度: {confidence:.2f}"
    
    def build_question_context(
        self, 
        session_data: Dict[str, Any], 
        use_psychological_context: bool,
        use_conversation_history: bool
    ) -> Dict[str, Any]:
        """构建问题生成的上下文信息"""
        context = {
            "candidate_info": {},
            "position_info": {},
            "psychological_context": {},
            "conversation_context": {}
        }
        
        # 候选人信息
        if session_data.get("application") and session_data["application"].get("resume"):
            context["candidate_info"] = {
                "name": session_data["application"]["resume"].get("candidate_name"),
                "content": session_data["application"]["resume"].get("content", "")
            }
        
        # 岗位信息
        if session_data.get("application") and session_data["application"].get("position"):
            context["position_info"] = {
                "title": session_data["application"]["position"].get("title"),
                "required_skills": session_data["application"]["position"].get("required_skills", []),
                "description": session_data["application"]["position"].get("description", "")
            }
        
        # 心理分析上下文
        if use_psychological_context and session_data.get("state_history"):
            latest_state = self._get_latest_psychological_state(session_data["state_history"])
            if latest_state:
                context["psychological_context"] = {
                    "current_emotion": latest_state.get("emotion", {}),
                    "engagement_level": latest_state.get("engagement", 0),
                    "nervousness_level": latest_state.get("nervousness", 0),
                    "confidence_level": latest_state.get("confidence_level", 0),
                    "depression_risk_trend": self._get_depression_risk_trend(session_data)
                }
        
        # 对话历史上下文
        if use_conversation_history and session_data.get("transcripts"):
            # 获取最近的对话记录
            transcripts = session_data["transcripts"]
            recent_transcripts = transcripts[-10:] if len(transcripts) > 10 else transcripts
            context["conversation_context"] = {
                "recent_topics": self._extract_topics_from_transcripts(recent_transcripts),
                "last_candidate_response": self._get_last_candidate_response(recent_transcripts),
                "conversation_flow": self._analyze_conversation_flow(recent_transcripts)
            }
        
        return context
    
    def _get_latest_psychological_state(self, state_history: List[Dict]) -> Optional[Dict]:
        """获取最新的心理状态"""
        if not state_history:
            return None
        return state_history[-1]
    
    def _get_depression_risk_trend(self, session_data: Dict) -> str:
        """获取抑郁风险趋势"""
        # 简化实现，实际应该分析历史数据
        return "stable"
    
    def _extract_topics_from_transcripts(self, transcripts: List[Dict]) -> List[str]:
        """从转录中提取话题（简化版）"""
        topics = []
        for transcript in transcripts:
            if transcript.get("speaker") == "interviewer":
                text = transcript.get("text", "")
                # 简单的关键词提取
                if "技术" in text or "开发" in text:
                    topics.append("技术能力")
                elif "团队" in text or "协作" in text:
                    topics.append("团队合作")
                elif "项目" in text or "经验" in text:
                    topics.append("项目经验")
        return list(set(topics))
    
    def _get_last_candidate_response(self, transcripts: List[Dict]) -> Optional[str]:
        """获取候选人的最后一次回答"""
        for transcript in reversed(transcripts):
            if transcript.get("speaker") == "candidate":
                return transcript.get("text", "")
        return None
    
    def _analyze_conversation_flow(self, transcripts: List[Dict]) -> str:
        """分析对话流程（简化版）"""
        if len(transcripts) < 3:
            return "opening"
        elif len(transcripts) < 10:
            return "warming_up"
        elif len(transcripts) < 20:
            return "deep_dive"
        else:
            return "closing"


# 单例实例
_immersive_agent = None


def get_immersive_interview_agent() -> ImmersiveInterviewAgent:
    """获取沉浸式面试AI助手实例"""
    global _immersive_agent
    
    if _immersive_agent is None:
        _immersive_agent = ImmersiveInterviewAgent()
    
    return _immersive_agent