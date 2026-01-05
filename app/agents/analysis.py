# -*- coding: utf-8 -*-
"""
综合分析评估代理（精简版）。
基于 Rubric 量表对候选人做多维度分析，并生成建议。
"""
from __future__ import annotations

import json
from typing import Dict, Any, List, Optional, Callable
from loguru import logger

from .llm_client import get_llm_client
from .prompts import get_prompt, get_config


class AnalysisService:
    """综合分析评估服务。"""

    def __init__(self, job_config: Dict[str, Any] | None = None):
        self.job_config = job_config or {}
        self._llm = get_llm_client()
        # 从 YAML 加载评估配置
        self._rubric_scales = get_config("analysis", "rubric_scales")
        self._evaluation_dimensions = get_config("analysis", "evaluation_dimensions")
        self._recommendation_levels = get_config("analysis", "recommendation_levels")

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
        for key, config in self._evaluation_dimensions.items():
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
            "rubric_scales": self._rubric_scales,
            "evaluation_dimensions": self._evaluation_dimensions,
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
        system_prompt = get_prompt(
            "analysis", "dimension_evaluation",
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
            logger.error("评估维度 {} 失败: {}", config["name"], exc)
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
        for level_key, cfg in self._recommendation_levels.items():
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
            system_prompt = get_prompt("analysis", "comprehensive_report")
            return await self._llm.complete(system_prompt, user_prompt, temperature=0.4)
        except Exception as exc:
            logger.error("生成综合报告失败: {}", exc)
            return f"""## {candidate_name} 综合分析报告

**综合得分**：{final_score}分
**推荐等级**：{recommendation['label']}
**建议行动**：{recommendation['action']}

由于生成失败，请参考各维度评分自行决策。"""


_analysis_service: AnalysisService | None = None


def get_analysis_service(job_config: Dict[str, Any] | None = None) -> AnalysisService:
    """获取 AnalysisService 单例。"""
    global _analysis_service
    if _analysis_service is None or job_config is not None:
        _analysis_service = AnalysisService(job_config)
    return _analysis_service
