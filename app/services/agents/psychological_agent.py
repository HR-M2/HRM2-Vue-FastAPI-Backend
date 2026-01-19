"""
心理分析 Agent 模块

基于面试记录的心理数据生成综合心理分析报告
"""
import logging
from typing import Dict, Any, List

from app.schemas.psychological import (
    PsychologicalAnalysisOutput,
    BigFiveAnalysis,
    BigFiveScores,
    DeceptionAnalysis,
    DepressionAnalysis,
    SpeechPatternAnalysis,
)
from .llm_client import get_llm_client

logger = logging.getLogger(__name__)


class PsychologicalAnalysisAgent:
    """心理分析 Agent"""
    
    SYSTEM_PROMPT = """你是一位专业的心理分析专家，专注于通过面试对话分析候选人的心理特征。

你的任务是基于以下数据生成心理分析报告：
1. 大五人格评分（开放性、尽责性、外向性、宜人性、神经质）
2. 欺骗检测评分
3. 抑郁风险评分
4. 发言模式统计

请严格按照要求的 JSON 格式输出分析结果。分析应当：
- 客观、专业、有建设性
- 基于数据而非臆测
- 提供有价值的建议
- 注意候选人隐私和尊严

注意：你的分析仅供参考，不构成临床诊断。"""

    def __init__(self):
        self.llm_client = get_llm_client()
    
    async def analyze(self, interview_data: Dict[str, Any]) -> PsychologicalAnalysisOutput:
        """
        执行心理分析
        
        参数:
            interview_data: 面试数据，包含统计信息和会话记录
            
        返回:
            PsychologicalAnalysisOutput: 分析结果
        """
        # 提取数据
        candidate_name = interview_data.get("candidate_name", "候选人")
        position_title = interview_data.get("position_title", "未知岗位")
        duration_seconds = interview_data.get("duration_seconds", 0)
        utterance_count = interview_data.get("utterance_count", {})
        char_count = interview_data.get("char_count", {})
        speaking_ratio = interview_data.get("speaking_ratio", {})
        big_five_average = interview_data.get("big_five_average", {})
        depression_average = interview_data.get("depression_average", {})
        conversation_history = interview_data.get("conversation_history", [])
        
        # 提取每条发言的心理评分
        big_five_scores_list = []
        deception_scores_list = []
        depression_scores_list = []
        
        for item in conversation_history:
            scores = item.get("candidate_scores")
            if scores:
                if scores.get("big_five"):
                    big_five_scores_list.append(scores["big_five"])
                if scores.get("deception"):
                    deception_scores_list.append(scores["deception"])
                if scores.get("depression"):
                    depression_scores_list.append(scores["depression"])
        
        # 计算欺骗检测平均分
        avg_deception = 0.0
        if deception_scores_list:
            avg_deception = sum(d.get("score", 0) for d in deception_scores_list) / len(deception_scores_list)
        
        # 构建用户提示
        user_prompt = self._build_user_prompt(
            candidate_name=candidate_name,
            position_title=position_title,
            duration_seconds=duration_seconds,
            utterance_count=utterance_count,
            char_count=char_count,
            speaking_ratio=speaking_ratio,
            big_five_average=big_five_average,
            depression_average=depression_average,
            avg_deception=avg_deception,
            big_five_scores_list=big_five_scores_list,
            deception_scores_list=deception_scores_list,
            depression_scores_list=depression_scores_list,
            conversation_history=conversation_history
        )
        
        # 调用 LLM
        try:
            result = await self.llm_client.complete_json(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3
            )
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            # 返回基于数据的默认分析
            return self._generate_fallback_result(
                big_five_average=big_five_average,
                depression_average=depression_average,
                avg_deception=avg_deception,
                speaking_ratio=speaking_ratio,
                char_count=char_count,
                utterance_count=utterance_count
            )
        
        # 解析结果
        return self._parse_result(result, big_five_average, depression_average, avg_deception, speaking_ratio, char_count, utterance_count)
    
    def _build_user_prompt(
        self,
        candidate_name: str,
        position_title: str,
        duration_seconds: float,
        utterance_count: Dict,
        char_count: Dict,
        speaking_ratio: Dict,
        big_five_average: Dict,
        depression_average: Dict,
        avg_deception: float,
        big_five_scores_list: List[Dict],
        deception_scores_list: List[Dict],
        depression_scores_list: List[Dict],
        conversation_history: List[Dict]
    ) -> str:
        """构建用户提示"""
        
        # 格式化面试时长
        duration_min = int(duration_seconds / 60)
        
        # 选取部分对话作为样本
        sample_conversations = []
        for i, item in enumerate(conversation_history[:10]):  # 最多取10条
            speaker = "面试官" if item.get("speaker") == "interviewer" else "候选人"
            text = item.get("text", "")[:200]  # 截断长文本
            sample_conversations.append(f"{speaker}: {text}")
        
        prompt = f"""请分析以下面试心理数据，生成综合心理分析报告。

## 基本信息
- 候选人: {candidate_name}
- 应聘岗位: {position_title}
- 面试时长: {duration_min} 分钟

## 发言统计
- 总发言次数: {utterance_count.get('total', 0)}
  - 面试官: {utterance_count.get('interviewer', 0)} 次
  - 候选人: {utterance_count.get('candidate', 0)} 次
- 总字数: {char_count.get('total', 0)}
  - 面试官: {char_count.get('interviewer', 0)} 字
  - 候选人: {char_count.get('candidate', 0)} 字
- 发言占比(按字数): 候选人 {speaking_ratio.get('by_chars', {}).get('candidate', 0) * 100:.1f}%

## 大五人格平均分 (0-1)
- 开放性 (Openness): {big_five_average.get('openness', 0.5):.3f}
- 尽责性 (Conscientiousness): {big_five_average.get('conscientiousness', 0.5):.3f}
- 外向性 (Extraversion): {big_five_average.get('extraversion', 0.5):.3f}
- 宜人性 (Agreeableness): {big_five_average.get('agreeableness', 0.5):.3f}
- 神经质 (Neuroticism): {big_five_average.get('neuroticism', 0.5):.3f}

## 欺骗检测
- 平均欺骗分数: {avg_deception:.3f} (0-1, 越低越可信)
- 检测次数: {len(deception_scores_list)}

## 抑郁风险
- 平均分数: {depression_average.get('score', 0):.1f} (0-100)
- 风险等级: {depression_average.get('level', 'unknown')}
- 检测次数: {len(depression_scores_list)}

## 对话样本
{chr(10).join(sample_conversations)}

---

请按以下 JSON 格式输出分析结果：

```json
{{
  "big_five_analysis": {{
    "personality_type": "人格类型概括，如'外向开放型'",
    "strengths": ["优势1", "优势2", "优势3"],
    "potential_concerns": ["潜在关注点1", "潜在关注点2"],
    "work_style": "工作风格建议",
    "team_fit": "团队适配建议"
  }},
  "deception_analysis": {{
    "credibility_level": "high/medium/low",
    "analysis_summary": "可信度分析总结"
  }},
  "depression_analysis": {{
    "trend": "stable/increasing/decreasing",
    "interpretation": "解读说明"
  }},
  "speech_pattern_analysis": {{
    "communication_style": "沟通风格描述",
    "fluency_assessment": "流畅度评估",
    "confidence_level": "high/medium/low"
  }},
  "overall_score": 85.0,
  "risk_level": "low/medium/high",
  "overall_summary": "综合评估摘要（100-200字）",
  "recommendations": ["建议1", "建议2", "建议3"],
  "report_markdown": "# 心理分析报告\\n\\n完整的 Markdown 格式报告..."
}}
```

注意：
1. overall_score 范围 0-100，综合考虑心理健康、可信度、情绪稳定性
2. risk_level 基于抑郁风险和整体心理状态
3. report_markdown 应包含详细分析，使用 Markdown 格式
"""
        return prompt
    
    def _parse_result(
        self,
        result: Dict[str, Any],
        big_five_average: Dict,
        depression_average: Dict,
        avg_deception: float,
        speaking_ratio: Dict,
        char_count: Dict,
        utterance_count: Dict
    ) -> PsychologicalAnalysisOutput:
        """解析 LLM 返回结果"""
        
        # 大五人格分析
        bf_analysis = result.get("big_five_analysis", {})
        big_five_analysis = BigFiveAnalysis(
            scores=BigFiveScores(
                openness=big_five_average.get("openness", 0.5),
                conscientiousness=big_five_average.get("conscientiousness", 0.5),
                extraversion=big_five_average.get("extraversion", 0.5),
                agreeableness=big_five_average.get("agreeableness", 0.5),
                neuroticism=big_five_average.get("neuroticism", 0.5),
            ),
            personality_type=bf_analysis.get("personality_type", ""),
            strengths=bf_analysis.get("strengths", []),
            potential_concerns=bf_analysis.get("potential_concerns", []),
            work_style=bf_analysis.get("work_style", ""),
            team_fit=bf_analysis.get("team_fit", "")
        )
        
        # 欺骗检测分析
        dec_analysis = result.get("deception_analysis", {})
        deception_analysis = DeceptionAnalysis(
            overall_score=avg_deception,
            credibility_level=dec_analysis.get("credibility_level", "unknown"),
            suspicious_responses=[],
            analysis_summary=dec_analysis.get("analysis_summary", "")
        )
        
        # 抑郁风险分析
        dep_analysis = result.get("depression_analysis", {})
        depression_analysis = DepressionAnalysis(
            average_score=depression_average.get("score", 0),
            risk_level=depression_average.get("level", "unknown"),
            trend=dep_analysis.get("trend", "stable"),
            high_risk_moments=[],
            interpretation=dep_analysis.get("interpretation", "")
        )
        
        # 发言模式分析
        sp_analysis = result.get("speech_pattern_analysis", {})
        candidate_ratio = speaking_ratio.get("by_chars", {}).get("candidate", 0)
        candidate_chars = char_count.get("candidate", 0)
        candidate_count = utterance_count.get("candidate", 0)
        avg_length = candidate_chars / candidate_count if candidate_count > 0 else 0
        
        speech_pattern_analysis = SpeechPatternAnalysis(
            speaking_ratio=candidate_ratio,
            total_chars=candidate_chars,
            avg_response_length=avg_length,
            response_count=candidate_count,
            communication_style=sp_analysis.get("communication_style", ""),
            fluency_assessment=sp_analysis.get("fluency_assessment", ""),
            confidence_level=sp_analysis.get("confidence_level", "")
        )
        
        return PsychologicalAnalysisOutput(
            big_five_analysis=big_five_analysis,
            deception_analysis=deception_analysis,
            depression_analysis=depression_analysis,
            speech_pattern_analysis=speech_pattern_analysis,
            overall_score=result.get("overall_score", 70.0),
            risk_level=result.get("risk_level", "low"),
            overall_summary=result.get("overall_summary", ""),
            recommendations=result.get("recommendations", []),
            report_markdown=result.get("report_markdown", "")
        )
    
    def _generate_fallback_result(
        self,
        big_five_average: Dict,
        depression_average: Dict,
        avg_deception: float,
        speaking_ratio: Dict,
        char_count: Dict,
        utterance_count: Dict
    ) -> PsychologicalAnalysisOutput:
        """生成基于数据的默认分析（当 LLM 调用失败时）"""
        
        # 大五人格分析
        big_five_analysis = BigFiveAnalysis(
            scores=BigFiveScores(
                openness=big_five_average.get("openness", 0.5),
                conscientiousness=big_five_average.get("conscientiousness", 0.5),
                extraversion=big_five_average.get("extraversion", 0.5),
                agreeableness=big_five_average.get("agreeableness", 0.5),
                neuroticism=big_five_average.get("neuroticism", 0.5),
            ),
            personality_type="待分析",
            strengths=[],
            potential_concerns=[],
            work_style="",
            team_fit=""
        )
        
        # 欺骗检测分析
        credibility = "high" if avg_deception < 0.3 else ("medium" if avg_deception < 0.6 else "low")
        deception_analysis = DeceptionAnalysis(
            overall_score=avg_deception,
            credibility_level=credibility,
            suspicious_responses=[],
            analysis_summary=f"欺骗分数 {avg_deception:.2f}，可信度{credibility}"
        )
        
        # 抑郁风险分析
        depression_analysis = DepressionAnalysis(
            average_score=depression_average.get("score", 0),
            risk_level=depression_average.get("level", "unknown"),
            trend="stable",
            high_risk_moments=[],
            interpretation=f"抑郁分数 {depression_average.get('score', 0):.1f}，风险等级 {depression_average.get('level', 'unknown')}"
        )
        
        # 发言模式分析
        candidate_ratio = speaking_ratio.get("by_chars", {}).get("candidate", 0)
        candidate_chars = char_count.get("candidate", 0)
        candidate_count = utterance_count.get("candidate", 0)
        avg_length = candidate_chars / candidate_count if candidate_count > 0 else 0
        
        speech_pattern_analysis = SpeechPatternAnalysis(
            speaking_ratio=candidate_ratio,
            total_chars=candidate_chars,
            avg_response_length=avg_length,
            response_count=candidate_count,
            communication_style="待分析",
            fluency_assessment="待分析",
            confidence_level="medium"
        )
        
        # 计算综合分数
        overall_score = 70.0
        risk_level = depression_average.get("level", "low")
        
        return PsychologicalAnalysisOutput(
            big_five_analysis=big_five_analysis,
            deception_analysis=deception_analysis,
            depression_analysis=depression_analysis,
            speech_pattern_analysis=speech_pattern_analysis,
            overall_score=overall_score,
            risk_level=risk_level,
            overall_summary="心理分析报告生成失败，显示基础数据统计。",
            recommendations=["建议重新生成报告以获取详细分析"],
            report_markdown="# 心理分析报告\n\n报告生成失败，请重试。"
        )
