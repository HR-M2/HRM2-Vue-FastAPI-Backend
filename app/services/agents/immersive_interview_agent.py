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
            return self._ensure_contextual_first(suggestions, context, count)
        except Exception as e:
            # 如果AI服务失败，回退到模拟数据
            logger.warning(f"AI问题生成失败，使用备用方案: {e}")
            suggestions = self._generate_mock_questions(
                count, difficulty, focus_areas, question_type, context
            )
            return self._ensure_contextual_first(suggestions, context, count)
    
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
你需要根据候选人的简历信息与对话上下文，生成智能的面试问题建议。

沉浸式面试的特点：
- 结合简历关键点进行针对性提问
- 结合对话历史保持话题连贯性
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
                    "psychological_context": "",
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

        conversation_context = context.get("conversation_context", {})
        conversation_desc = "暂无对话历史"
        last_response_quote = ""
        if conversation_context:
            recent_topics = conversation_context.get("recent_topics", [])
            last_response = conversation_context.get("last_candidate_response", "")
            flow_stage = conversation_context.get("conversation_flow", "opening")
            conversation_desc = f"最近话题: {', '.join(recent_topics) if recent_topics else '无'}, 对话阶段: {flow_stage}"
            if last_response:
                conversation_desc += f", 最后回答: {last_response[:100]}..."
                last_response_quote = f"\n\n最后一次候选人回答原文（节选）:\n\"{last_response[:120]}\""

        candidate_info = context.get("candidate_info", {})
        resume_content = candidate_info.get("content", "")

        position_info = context.get("position_info", {})
        position_title = position_info.get("title", "未知")
        required_skills = position_info.get("required_skills", [])
        position_desc = position_info.get("description", "")

        prompt = f"""# 面试问题生成请求

## 基本要求
- 生成问题数量: {count}
- 问题难度: {difficulty}
- 问题类型: {question_type}
- 关注领域: {', '.join(focus_areas) if focus_areas else '无特定要求'}

## 候选人简历信息
- 姓名: {candidate_info.get('name', '未知')}
- 简历内容（节选）:
{resume_content[:1200]}

## 岗位信息
- 职位: {position_title}
- 技能要求: {', '.join(required_skills) if required_skills else '未指定'}
- 职位描述（节选）:
{position_desc[:800]}

## 对话上下文
{conversation_desc}{last_response_quote}

## 生成规则
0. 如果存在对话上下文（不是“暂无对话历史”），请确保 suggestions[0] 必须是承接上下文的追问（优先围绕“最后一次候选人回答原文（节选）”，其次围绕最近话题），并将该条 priority 设置为 1
0.1 追问要求：问题要短、直接、单句为主，不要大段陈述；尽量引用候选人原话中的短片段（用引号，<=20字）作为锚点再追问；尽量只问一个点，避免一问多问
1. 问题要同时贴合岗位要求与候选人简历中的具体经历/项目/技能点
2. 如果对话上下文中已有话题，优先生成与当前话题连续的追问
3. 避免重复已经问过的问题
4. 提供清晰的提问时机建议

## JSON返回格式
{{
  "suggestions": [
    {{
      "question": "完整的问题内容",
      "type": "问题类型 (technical/behavioral/situational/mixed)",
      "priority": 1,
      "reason": "推荐原因",
      "timing_suggestion": "提问时机建议",
      "expected_response_indicators": ["技术深度", "表达清晰度"]
    }}
  ]
}}

请直接返回JSON，不要包含其他内容。"""

        # print(prompt)
        return prompt

    def _ensure_contextual_first(
        self,
        suggestions: List[Dict[str, Any]],
        context: Dict[str, Any],
        count: int
    ) -> List[Dict[str, Any]]:
        conversation_context = context.get("conversation_context", {})
        if not conversation_context:
            return suggestions

        last_response = conversation_context.get("last_candidate_response")
        recent_topics = conversation_context.get("recent_topics", [])
        if not last_response and not recent_topics:
            return suggestions

        def _score_question(text: str) -> int:
            if not text:
                return 0

            score = 0
            if "你刚才" in text or "刚才" in text or "你提到" in text or "继续" in text or "追问" in text:
                score += 3

            if last_response:
                frag = str(last_response)[:12]
                if frag and frag in text:
                    score += 6

            for topic in recent_topics or []:
                if topic and str(topic) in text:
                    score += 2

            return score

        best_idx = -1
        best_score = -1
        for idx, s in enumerate(suggestions):
            q = s.get("question", "")
            sc = _score_question(q)
            if sc > best_score:
                best_score = sc
                best_idx = idx

        if best_idx > 0 and best_score > 0:
            suggestions = [suggestions[best_idx]] + suggestions[:best_idx] + suggestions[best_idx + 1:]
        elif best_score <= 0:
            if last_response:
                snippet = str(last_response).replace("\n", " ").strip()[:18]
                question = f"你刚才说“{snippet}…”，能举个具体例子吗？"
            else:
                topic = str(recent_topics[0])
                question = f"关于“{topic}”，你能给一个你亲自做过的例子吗？"

            suggestions = [{
                "question": question,
                "type": "followup",
                "priority": 1,
                "reason": "基于对话上下文的追问，保证话题连贯并验证细节",
                "psychological_context": "",
                "timing_suggestion": "建议紧接上一轮对话追问",
                "expected_response_indicators": [
                    "技术深度",
                    "表达清晰度"
                ]
            }] + suggestions

        suggestions = suggestions[:count]

        if suggestions:
            for i, s in enumerate(suggestions):
                s["priority"] = i + 1

        return suggestions

    def build_question_context(
        self,
        session_data: Dict[str, Any],
        use_psychological_context: bool,
        use_conversation_history: bool
    ) -> Dict[str, Any]:
        """构建问题生成的上下文信息"""
        context: Dict[str, Any] = {
            "candidate_info": {},
            "position_info": {},
            "conversation_context": {}
        }

        if session_data.get("application") and session_data["application"].get("resume"):
            context["candidate_info"] = {
                "name": session_data["application"]["resume"].get("candidate_name"),
                "content": session_data["application"]["resume"].get("content", "")
            }

        if session_data.get("application") and session_data["application"].get("position"):
            context["position_info"] = {
                "title": session_data["application"]["position"].get("title"),
                "required_skills": session_data["application"]["position"].get("required_skills", []),
                "description": session_data["application"]["position"].get("description", "")
            }

        if use_conversation_history and session_data.get("transcripts"):
            transcripts = session_data["transcripts"]
            recent_transcripts = transcripts[-10:] if len(transcripts) > 10 else transcripts
            context["conversation_context"] = {
                "recent_topics": self._extract_topics_from_transcripts(recent_transcripts),
                "last_candidate_response": self._get_last_candidate_response(recent_transcripts),
                "conversation_flow": self._analyze_conversation_flow(recent_transcripts)
            }

        return context

    def _generate_mock_questions(
        self,
        count: int,
        difficulty: str,
        focus_areas: Optional[List[str]],
        question_type: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成模拟问题建议（AI服务失败时的备用方案）"""

        suggestions: List[Dict[str, Any]] = []
        conversation_context = context.get("conversation_context", {})
        candidate_info = context.get("candidate_info", {})
        resume_content = candidate_info.get("content", "")
        last_response = conversation_context.get("last_candidate_response")
        recent_topics = conversation_context.get("recent_topics", [])

        for i in range(count):
            if last_response:
                snippet = str(last_response).replace("\n", " ").strip()[:18]
                question = f"你刚才说“{snippet}…”，这里你是怎么做取舍的？"
                question_type_actual = "followup"
                reason = "基于候选人上一轮回答进行追问，验证细节与思考过程"
                timing_suggestion = "建议紧接上一轮回答追问"
            elif resume_content:
                question = f"结合你的简历经历，挑一个你最有成就感的项目，说说你的具体贡献与难点（{difficulty}）。"
                question_type_actual = "behavioral"
                reason = "基于简历信息提问，确保问题有针对性"
                timing_suggestion = "适合在开场或话题切换时提问"
            elif "技术能力" in recent_topics:
                question = f"围绕刚才的技术话题，能给一个更具体的实现细节或数据指标吗？（{difficulty}）"
                question_type_actual = "technical"
                reason = "基于对话话题继续深入，补充可验证细节"
                timing_suggestion = "适合在当前话题结束前提问"
            else:
                question = f"我们继续聊聊你的项目经历：你遇到过最棘手的问题是什么？你怎么解决的？（{difficulty}）"
                question_type_actual = "behavioral"
                reason = "在缺少足够上下文时，使用通用但可展开的问题"
                timing_suggestion = "适合在任意阶段提问"

            suggestion = {
                "question": question,
                "type": question_type_actual,
                "priority": max(1, count - i),
                "reason": reason,
                "psychological_context": "",
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