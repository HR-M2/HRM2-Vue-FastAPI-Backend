# -*- coding: utf-8 -*-
"""
面试助手 Agent（精简版）。
功能：面试问题生成、回答评估、追问建议、动态追问、模拟候选人回答、最终报告。
"""
from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from loguru import logger

from .llm_client import get_llm_client
from .prompts import get_prompt, get_config


class InterviewService:
    """面试助手服务。"""

    def __init__(self, job_config: Dict[str, Any] | None = None):
        self.job_config = job_config or {}
        self._llm = get_llm_client()

    async def generate_initial_questions(self, resume_content: str, count: int = 3, interest_point_count: int = 2) -> Dict[str, Any]:
        """基于简历生成首轮问题与兴趣点。"""
        if not resume_content:
            return {"questions": [], "interest_points": []}

        job_title = self.job_config.get("title", "未指定职位")
        job_description = self.job_config.get("description", "")
        job_requirements = json.dumps(self.job_config.get("requirements", {}), ensure_ascii=False, indent=2)

        system_prompt = get_config("interview", "system_prompts.resume_question")
        user_prompt = get_prompt(
            "interview", "resume_based_question",
            resume_content=resume_content[:5000],
            job_title=job_title,
            job_description=job_description,
            job_requirements=job_requirements,
            count=count,
            interest_point_count=interest_point_count,
        )

        try:
            result = await self._llm.complete_json(system_prompt, user_prompt, temperature=0.7)
        except Exception as exc:
            logger.error("生成简历问题失败: {}", exc)
            return {"questions": [], "interest_points": []}

        questions = []
        for q in result.get("questions", [])[:count]:
            questions.append(
                {
                    "question": q.get("question", ""),
                    "category": q.get("category", "简历相关"),
                    "difficulty": q.get("difficulty", 6),
                    "expected_skills": q.get("expected_skills", []),
                    "source": "resume",
                }
            )

        points = []
        for p in result.get("interest_points", [])[:interest_point_count]:
            if isinstance(p, dict):
                points.append(
                    {
                        "content": p.get("content", p.get("point", "")),
                        "reason": p.get("reason", ""),
                        "question": p.get("question", ""),
                    }
                )
            else:
                points.append({"content": str(p), "reason": "", "question": f"请介绍您在{p}方面的经验"})

        return {"questions": questions, "interest_points": points}

    async def generate_skill_based_questions(self, category: str, candidate_level: str = "senior", count: int = 2) -> List[Dict[str, Any]]:
        """基于技能/类别生成问题。"""
        job_title = self.job_config.get("title", "未指定职位")
        system_prompt = get_config("interview", "system_prompts.skill_question")
        user_prompt = get_prompt(
            "interview", "skill_based_question",
            job_title=job_title,
            candidate_level=candidate_level,
            question_category=category,
            count=count,
        )
        try:
            result = await self._llm.complete_json(system_prompt, user_prompt, temperature=0.7)
        except Exception as exc:
            logger.error("生成技能问题失败: {}", exc)
            return []

        questions: List[Dict[str, Any]] = []
        for q in result.get("questions", [])[:count]:
            questions.append(
                {
                    "question": q.get("question", ""),
                    "category": category,
                    "difficulty": q.get("difficulty", 6),
                    "expected_skills": q.get("expected_skills", []),
                    "source": "skill",
                }
            )
        return questions

    async def generate_adaptive_questions(
        self,
        current_question: str,
        current_answer: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        resume_summary: str = "",
        followup_count: int = 2,
        alternative_count: int = 3,
    ) -> List[Dict[str, Any]]:
        """基于当前回答生成后续问题。"""
        job_title = self.job_config.get("title", "未指定职位")
        job_requirements = json.dumps(self.job_config.get("requirements", {}), ensure_ascii=False, indent=2)
        history_text = ""
        if conversation_history:
            for msg in conversation_history:
                role_label = "面试官" if msg.get("role") == "interviewer" else "候选人"
                history_text += f"{role_label}: {msg.get('content', '')}\n"
        else:
            history_text = "（首次提问）"

        system_prompt = get_config("interview", "system_prompts.adaptive_question")
        user_prompt = get_prompt(
            "interview", "candidate_questions",
            job_title=job_title,
            job_requirements=job_requirements,
            resume_summary=resume_summary or "（未提供简历摘要）",
            conversation_history=history_text,
            current_question=current_question,
            current_answer=current_answer,
            followup_count=followup_count,
            alternative_count=alternative_count,
        )
        total = followup_count + alternative_count
        try:
            result = await self._llm.complete_json(system_prompt, user_prompt, temperature=0.7)
            questions = []
            for q in result.get("candidate_questions", [])[:total]:
                questions.append(
                    {
                        "question": q.get("question", ""),
                        "purpose": q.get("purpose", ""),
                        "expected_skills": q.get("expected_skills", []),
                        "source": q.get("source", "followup"),
                    }
                )
            return questions
        except Exception as exc:
            logger.error("自适应问题生成失败: {}", exc)
            return []

    async def simulate_candidate_answer(
        self,
        question: str,
        resume_content: str,
        position_title: str,
        position_description: str,
        candidate_name: str,
        candidate_type: str,
        conversation_history: str = "",
    ) -> str:
        """模拟候选人回答，用于测试/演练。"""
        type_descriptions = get_config("interview", "candidate_type_descriptions")
        type_desc = type_descriptions.get(candidate_type, type_descriptions.get("ideal", ""))
        
        user_prompt = get_prompt(
            "interview", "simulate_candidate_answer",
            resume_content=resume_content,
            position_title=position_title,
            position_description=position_description,
            candidate_name=candidate_name,
            candidate_type=candidate_type,
            type_description=type_desc,
            conversation_history=conversation_history or "（无历史）",
            question=question,
        )
        system_prompt = get_config("interview", "system_prompts.simulate_answer")
        return await self._llm.complete(system_prompt, user_prompt, temperature=0.8)

    async def generate_final_report(self, candidate_name: str, messages: List[Dict[str, Any]], hr_notes: str = "") -> Dict[str, Any]:
        """生成最终面试报告。"""
        job_title = self.job_config.get("title", "未指定职位")
        conversation_log = self._format_conversation_log(messages)
        system_prompt = get_config("interview", "system_prompts.final_report")
        user_prompt = get_prompt(
            "interview", "final_report",
            candidate_name=candidate_name,
            job_title=job_title,
            hr_notes=hr_notes or "无",
            conversation_log=conversation_log,
        )
        try:
            return await self._llm.complete_json(system_prompt, user_prompt, temperature=0.4)
        except Exception as exc:
            logger.error("最终报告生成失败: {}", exc)
            return {
                "overall_assessment": {
                    "recommendation_score": 50,
                    "recommendation": "待定",
                    "summary": f"候选人{candidate_name}完成了面试，建议人工复核。",
                },
                "dimension_analysis": {},
                "skill_assessment": [],
                "highlights": [],
                "red_flags": [],
                "overconfidence_detected": False,
                "suggested_next_steps": [],
            }

    # ========== 内部辅助 ==========

    def _format_conversation_log(self, messages: List[Dict[str, Any]]) -> str:
        """格式化对话日志为文本。"""
        lines = []
        for msg in messages or []:
            role_label = "面试官" if msg.get("role") == "interviewer" else "候选人"
            lines.append(f"[{msg.get('seq', 0)}] **{role_label}**: {msg.get('content', '')}")
        return "\n".join(lines)


_interview_service: InterviewService | None = None


def get_interview_service(job_config: Dict[str, Any] | None = None) -> InterviewService:
    """获取 InterviewService 单例。"""
    global _interview_service
    if _interview_service is None or job_config is not None:
        _interview_service = InterviewService(job_config)
    return _interview_service
