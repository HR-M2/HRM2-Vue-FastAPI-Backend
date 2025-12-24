"""
综合分析评估代理（精简版）。
基于 Rubric 量表对候选人做多维度分析，并生成建议。
"""
from __future__ import annotations

import json
import logging
from typing import Dict, Any, List, Optional, Callable

from .llm_client import get_llm_client

logger = logging.getLogger(__name__)

# ================= 量表与提示词 =================

RUBRIC_SCALES = {
    5: {"label": "卓越", "description": "远超岗位要求，表现突出"},
    4: {"label": "优秀", "description": "超出岗位要求，表现良好"},
    3: {"label": "良好", "description": "符合岗位要求，表现合格"},
    2: {"label": "一般", "description": "基本符合，但有提升空间"},
    1: {"label": "不足", "description": "未达到岗位要求"},
}

EVALUATION_DIMENSIONS = {
    "professional_competency": {
        "name": "专业能力",
        "weight": 0.30,
        "sub_dimensions": [
            "核心技能掌握程度",
            "专业知识深度",
            "问题解决能力",
            "学习成长潜力",
        ],
    },
    "work_experience": {
        "name": "工作经验",
        "weight": 0.25,
        "sub_dimensions": [
            "经验相关性",
            "项目复杂度",
            "成果可量化性",
            "职责承担程度",
        ],
    },
    "soft_skills": {
        "name": "软技能",
        "weight": 0.20,
        "sub_dimensions": [
            "沟通表达能力",
            "团队协作意识",
            "压力应对能力",
            "主动性与责任心",
        ],
    },
    "cultural_fit": {
        "name": "文化匹配",
        "weight": 0.15,
        "sub_dimensions": [
            "职业价值观",
            "工作态度",
            "发展意愿",
            "稳定性预期",
        ],
    },
    "interview_performance": {
        "name": "面试表现",
        "weight": 0.10,
        "sub_dimensions": [
            "回答逻辑性",
            "思维深度",
            "应变能力",
            "自我认知准确性",
        ],
    },
}

RECOMMENDATION_LEVELS = {
    "strong_recommend": {
        "min_score": 85,
        "label": "强烈推荐",
        "action": "建议优先录用，尽快安排后续流程",
    },
    "recommend": {"min_score": 70, "label": "推荐录用", "action": "符合要求，可以录用"},
    "cautious": {"min_score": 55, "label": "谨慎考虑", "action": "存在一定风险，建议进一步评估"},
    "not_recommend": {"min_score": 0, "label": "不推荐", "action": "不建议录用"},
}

SYSTEM_PROMPT_DIMENSION = """你是一位资深的人力资源评估专家，擅长基于 Rubric 量表进行候选人评估。

你需要评估候选人的【{dimension_name}】维度。

## Rubric 评分标准（1-5分）
- 5分 卓越：远超岗位要求，表现突出
- 4分 优秀：超出岗位要求，表现良好
- 3分 良好：符合岗位要求，表现合格
- 2分 一般：基本符合，但有提升空间
- 1分 不足：未达到岗位要求

## 子维度评估项
{sub_dimensions_block}

## 输出要求
请输出严格的 JSON 格式：
{{
    "dimension_score": <1-5的整数>,
    "sub_scores": {{
        "{sd0}": <1-5>,
        "{sd1}": <1-5>,
        "{sd2}": <1-5>,
        "{sd3}": <1-5>
    }},
    "strengths": ["优势1", "优势2"],
    "weaknesses": ["不足1", "不足2"],
    "analysis": "详细分析说明（100-200字）"
}}"""

SYSTEM_PROMPT_REPORT = """你是一位资深的招聘决策专家，擅长撰写专业的候选人综合评估报告。

请根据各维度评估结果，生成一份结构清晰、内容专业的综合分析报告。

报告要求：
1. 语言专业、客观、有建设性
2. 重点突出关键发现
3. 给出明确的录用建议
4. 控制在500字以内"""


class CandidateComprehensiveAnalyzer:
    """单人综合分析评估器（精简版）。"""

    def __init__(self, job_config: Dict[str, Any] | None = None):
        self.job_config = job_config or {}
        self._llm = get_llm_client()

    async def analyze(
        self,
        candidate_name: str,
        resume_content: str,
        screening_report: Dict[str, Any],
        interview_records: List[Dict[str, Any]],
        interview_report: Dict[str, Any],
        video_analysis: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> Dict[str, Any]:
        """执行综合分析。"""

        def update_progress(step: str, percent: int):
            if progress_callback:
                progress_callback(step, percent)

        update_progress("准备数据", 5)
        candidate_profile = self._build_candidate_profile(
            candidate_name=candidate_name,
            resume_content=resume_content,
            screening_report=screening_report,
            interview_records=interview_records,
            interview_report=interview_report,
            video_analysis=video_analysis,
        )

        dimension_scores: Dict[str, Dict[str, Any]] = {}
        current_percent = 10
        for key, config in EVALUATION_DIMENSIONS.items():
            dimension_scores[key] = await self._evaluate_dimension(key, candidate_profile, config)
            current_percent = min(90, current_percent + 20)
            update_progress(f"评估-{config['name']}", current_percent)

        final_score = self._calculate_final_score(dimension_scores)
        recommendation = self._determine_recommendation(final_score)
        report = await self._generate_comprehensive_report(
            candidate_name, candidate_profile, dimension_scores, final_score, recommendation
        )

        update_progress("完成", 100)
        return {
            "candidate_name": candidate_name,
            "final_score": final_score,
            "recommendation": recommendation,
            "dimension_scores": dimension_scores,
            "comprehensive_report": report,
            "rubric_scales": RUBRIC_SCALES,
            "evaluation_dimensions": EVALUATION_DIMENSIONS,
        }

    def _build_candidate_profile(
        self,
        candidate_name: str,
        resume_content: str,
        screening_report: Dict[str, Any],
        interview_records: List[Dict[str, Any]],
        interview_report: Dict[str, Any],
        video_analysis: Optional[Dict[str, Any]],
    ) -> str:
        """构建候选人画像文本。"""
        parts: List[str] = [
            f"# 候选人：{candidate_name}",
            f"## 应聘岗位：{self.job_config.get('title', '未指定')}",
            "\n## 一、简历内容",
            resume_content[:3000] if resume_content else "无简历内容",
            "\n## 二、简历初筛报告",
        ]
        if screening_report:
            parts.append(f"初筛评分：{screening_report.get('comprehensive_score', 'N/A')}")
            parts.append(f"初筛摘要：{screening_report.get('summary', screening_report.get('screening_summary', ''))}")
        else:
            parts.append("无初筛报告")

        parts.append("\n## 三、面试问答记录")
        if interview_records:
            for msg in interview_records:
                role = msg.get("role", "")
                content = msg.get("content", "")
                role_label = "面试官" if role == "interviewer" else "候选人"
                parts.append(f"**{role_label}**：{content}")
        else:
            parts.append("无面试记录")

        parts.append("\n## 四、面试分析报告")
        if interview_report:
            overall = interview_report.get("overall_assessment", {})
            parts.append(f"面试评分：{overall.get('recommendation_score', 'N/A')}")
            parts.append(f"面试建议：{overall.get('recommendation', 'N/A')}")
            parts.append(f"总结：{overall.get('summary', '')}")
            if interview_report.get("highlights"):
                parts.append(f"亮点：{', '.join(interview_report['highlights'])}")
            if interview_report.get("red_flags"):
                parts.append(f"风险点：{', '.join(interview_report['red_flags'])}")
        else:
            parts.append("无面试报告")

        if video_analysis:
            parts.append("\n## 五、面试视频分析")
            parts.append(json.dumps(video_analysis, ensure_ascii=False, indent=2))

        return "\n".join(parts)

    async def _evaluate_dimension(self, key: str, profile: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """按维度评估。"""
        subs = config["sub_dimensions"]
        system_prompt = SYSTEM_PROMPT_DIMENSION.format(
            dimension_name=config["name"],
            sub_dimensions_block="\n".join(f"- {sd}" for sd in subs),
            sd0=subs[0],
            sd1=subs[1],
            sd2=subs[2],
            sd3=subs[3],
        )
        user_prompt = f"请基于以下候选人资料，评估其【{config['name']}】维度：\n\n{profile}\n\n请严格按照 Rubric 量表给出评分和分析。"

        try:
            result = await self._llm.complete_json(system_prompt, user_prompt, temperature=0.3)
            result["weight"] = config["weight"]
            result["dimension_name"] = config["name"]
            return result
        except Exception as exc:
            logger.error("评估维度 %s 失败: %s", config["name"], exc)
            return {
                "dimension_score": 3,
                "sub_scores": {sd: 3 for sd in subs},
                "strengths": [],
                "weaknesses": [],
                "analysis": f"评估过程异常：{exc}",
                "weight": config["weight"],
                "dimension_name": config["name"],
            }

    def _calculate_final_score(self, dimension_scores: Dict[str, Dict[str, Any]]) -> float:
        """计算加权百分制得分。"""
        total_weighted = 0.0
        total_weight = 0.0
        for dim in dimension_scores.values():
            score = dim.get("dimension_score", 3)
            weight = dim.get("weight", 0.2)
            normalized = (score - 1) / 4 * 100
            total_weighted += normalized * weight
            total_weight += weight
        return round(total_weighted / total_weight, 1) if total_weight else 60.0

    def _determine_recommendation(self, final_score: float) -> Dict[str, Any]:
        """根据分数匹配推荐等级。"""
        for level_key, cfg in RECOMMENDATION_LEVELS.items():
            if final_score >= cfg["min_score"]:
                return {
                    "level": level_key,
                    "label": cfg["label"],
                    "action": cfg["action"],
                    "score": final_score,
                }
        return {"level": "not_recommend", "label": "不推荐", "action": "不建议录用", "score": final_score}

    async def _generate_comprehensive_report(
        self,
        candidate_name: str,
        profile: str,
        dimension_scores: Dict[str, Any],
        final_score: float,
        recommendation: Dict[str, Any],
    ) -> str:
        """生成综合报告文本。"""
        summary_lines = []
        for dim in dimension_scores.values():
            summary_lines.append(f"- {dim.get('dimension_name', '')}：{dim.get('dimension_score', 3)}分 - {dim.get('analysis', '')}")
        user_prompt = f"""请为候选人【{candidate_name}】生成综合分析报告：

## 评估结果
- 综合得分：{final_score}分
- 推荐等级：{recommendation['label']}
- 建议行动：{recommendation['action']}

## 各维度评估
{chr(10).join(summary_lines)}

请生成一份专业的综合分析报告，包含：
1. 候选人综合评价（一句话概括）
2. 核心优势（2-3点）
3. 潜在风险（1-2点）
4. 最终建议"""
        try:
            return await self._llm.complete(SYSTEM_PROMPT_REPORT, user_prompt, temperature=0.4)
        except Exception as exc:
            logger.error("生成综合报告失败: %s", exc)
            return f"""## {candidate_name} 综合分析报告

**综合得分**：{final_score}分
**推荐等级**：{recommendation['label']}
**建议行动**：{recommendation['action']}

由于生成失败，请参考各维度评分自行决策。"""
