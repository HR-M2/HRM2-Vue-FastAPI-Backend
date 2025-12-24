"""
面试助手 Agent（精简版）。
功能：面试问题生成、回答评估、追问建议、动态追问、模拟候选人回答、最终报告。
"""
from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from loguru import logger

from .llm_client import get_llm_client

# ================== 提示词模板 ==================

RESUME_BASED_QUESTION_PROMPT = """基于以下简历内容，为面试官生成针对性的面试问题。

# 简历内容
{resume_content}

# 职位信息
职位: {job_title}
职位描述: {job_description}
职位要求: {job_requirements}

# 要求
1. 分析简历中的关键点，识别{interest_point_count}个值得深入探讨的兴趣点
2. 每个兴趣点要生成对应的面试问题
3. 额外生成{count}个高质量面试问题
4. 问题应该：
   - 针对简历中具体内容，避免泛泛而谈
   - 能有效验证候选人的真实能力
   - 难度适中（5-8分，满分10分）
   - 覆盖技术能力和实际经验

# JSON返回格式
{{
    "interest_points": [
        {{
            "content": "兴趣点的简短描述（如：在XX公司主导了微服务改造项目）",
            "reason": "为什么这个点值得关注",
            "question": "针对这个兴趣点的面试问题"
        }}
    ],
    "questions": [
        {{
            "question": "问题内容",
            "category": "简历相关",
            "difficulty": 6,
            "expected_skills": ["技能1", "技能2"],
            "related_point": "对应的兴趣点"
        }}
    ]
}}

请直接返回JSON，不要包含其他内容。"""

SKILL_BASED_QUESTION_PROMPT = """基于以下信息生成面试问题。

职位: {job_title}
候选人级别: {candidate_level}
问题类别: {question_category}

# 级别难度对应
- junior (初级): 难度3-5分
- mid (中级): 难度5-7分
- senior (高级): 难度7-9分
- expert (专家): 难度8-10分

# 要求
1. 生成{count}个该类别的高质量问题
2. 问题难度应匹配候选人级别
3. 问题应该能有效考察相关技能
4. 避免太宽泛或太理论的问题
5. 优先考察实际经验和问题解决能力

# JSON返回格式
{{
    "questions": [
        {{
            "question": "问题内容",
            "difficulty": 7,
            "expected_skills": ["技能1", "技能2"],
            "evaluation_points": ["评估要点1", "评估要点2"]
        }}
    ]
}}

请直接返回JSON，不要包含其他内容。"""

ANSWER_EVALUATION_PROMPT = """请评估候选人的回答质量，特别注意识别**过度自信**和**不懂装懂**的信号。

问题: {question}
候选人回答: {answer}
考察技能: {target_skills}
问题难度: {difficulty}/10

## 评估维度 (每个维度1-4分)
### 1. 技术深度 (technical_depth)
- 1分: 仅知道概念名称，无法解释原理
- 2分: 理解基本原理，但缺乏深度
- 3分: 深入理解原理，能举实例
- 4分: 精通原理，能分析边界情况和trade-offs

### 2. 实践经验 (practical_experience)
- 1分: 无法提供具体项目细节
- 2分: 有项目但细节模糊
- 3分: 提供了具体的项目经验和数据
- 4分: 详细描述了复杂场景和解决方案

### 3. 回答具体性 (answer_specificity)
- 1分: 完全没有具体细节或数据
- 2分: 偶尔提到细节但不完整
- 3分: 包含多个具体参数、配置或代码
- 4分: 充满量化指标、架构图、代码示例

### 4. 逻辑清晰度 (logical_clarity)
- 1分: 混乱无条理
- 2分: 基本有条理
- 3分: 结构清晰
- 4分: 逻辑严密、层次分明

### 5. 诚实度 (honesty)
- 1分: 明显不懂装懂
- 2分: 有夸大倾向
- 3分: 比较诚实
- 4分: 准确认知自己的边界

### 6. 沟通能力 (communication)
- 1分: 表达不清
- 2分: 基本能说清楚
- 3分: 表达清晰
- 4分: 表达精准且有感染力

## 过度自信信号（重点关注）
- 使用高级专业术语但缺乏具体细节
- 回答模糊、使用大量不确定词汇
- 提到专业概念但没有具体数据、指标或案例示例
- 回答过短（<150字）但谈论复杂话题
- 缺乏对方案权衡的深入思考

## JSON返回格式
{{
    "dimension_scores": {{
        "technical_depth": 数字(1-4),
        "practical_experience": 数字(1-4),
        "answer_specificity": 数字(1-4),
        "logical_clarity": 数字(1-4),
        "honesty": 数字(1-4),
        "communication": 数字(1-4)
    }},
    "normalized_score": 标准化分数(0-100),
    "feedback": "各维度的具体反馈文字",
    "confidence_level": "genuine/uncertain/overconfident",
    "should_followup": true或false,
    "followup_reason": "追问原因（如果需要追问）",
    "followup_direction": "追问建议方向"
}}

重要：normalized_score 计算方式：
- 6个维度平均分 × 25 = 基础分
- 根据confidence_level调整（overconfident扣10分）

请直接返回JSON，不要包含其他内容。"""

FOLLOWUP_SUGGESTION_PROMPT = """基于候选人的回答，生成追问建议，以验证其真实能力水平。

原问题: {original_question}
候选人回答: {answer}
评估反馈: {evaluation_feedback}
目标技能: {target_skill}

## 追问策略
1. **要求具体化**：如果候选人提到技术概念，要求给出具体参数、指标、代码示例
2. **深入原理**：询问底层实现原理、工作机制、源码细节
3. **实战问题**：询问实际项目中遇到的具体问题和解决方案
4. **边界情况**：询问异常情况、性能瓶颈、容错处理
5. **技术对比**：要求对比不同方案的优劣、trade-off分析
6. **量化指标**：要求给出具体的性能数据、并发量、响应时间等

## JSON返回格式
{{
    "followup_suggestions": [
        {{
            "question": "追问问题",
            "purpose": "追问目的",
            "difficulty": 7
        }}
    ],
    "hr_hint": "给HR的建议提示"
}}

请直接返回JSON，不要包含其他内容。"""

CANDIDATE_QUESTIONS_PROMPT = """基于当前面试上下文，为面试官生成下一步的候选提问。

# 岗位信息
职位: {job_title}
职位要求: {job_requirements}

# 简历摘要
{resume_summary}

# 已完成的面试对话
{conversation_history}

# 当前轮次
问题: {current_question}
候选人回答: {current_answer}

# 第一步：分析候选人回答类型
请先判断候选人的回答属于哪种类型：
- clarification_request: 候选人请求澄清问题、要求举例、要求进一步说明
- counter_question: 候选人反问面试官
- off_topic: 候选人回答偏离主题
- normal_answer: 候选人正常回答问题

# 第二步：根据回答类型生成候选问题
请生成 {followup_count} 个追问问题（source: followup）+ {alternative_count} 个候选问题（source: resume 或 job）：

1. 如果是 clarification_request：
   - 生成对原问题的补充说明，给出具体示例或进一步解释
   - 或者换一种更具体、更有针对性的方式重新提问
   - 例如："比如您在XX公司主导了微服务改造项目，您能否具体说说当时的情况？您能否分享一个具体的项目经验和数据？"

2. 如果是 counter_question：
   - 简要回答候选人的问题后，回归到原始的问题
   - 例如："关于XXX，我理解的是……您能否分享一下您的看法？"

3. 如果是 off_topic：
   - 礼貌地将候选人回答带回正题
   - 或者从候选人的回答中找出可以深入讨论的点

4. 如果是 normal_answer：
   - 针对回答中值得深入讨论的点进行追问
   - 或者转向简历/岗位要求中尚未覆盖的重要领域
   - 避免重复已问过的问题
   - 难度适中，能有效验证候选人能力

# JSON返回格式
{{
    "answer_type": "回答类型：clarification_request/counter_question/off_topic/normal_answer",
    "candidate_questions": [
        {{
            "question": "基于当前回答的追问问题",
            "purpose": "验证XX能力",
            "expected_skills": ["技能1"],
            "source": "followup"
        }},
        {{
            "question": "基于简历的问题",
            "purpose": "考察XX经验",
            "expected_skills": ["技能2"],
            "source": "resume"
        }},
        {{
            "question": "基于岗位要求的问题",
            "purpose": "确认XX匹配度",
            "expected_skills": ["技能3"],
            "source": "job"
        }}
    ]
}}

重要：
- 必须根据候选人的实际回答内容生成问题，不要忽略候选人的反馈
- question 字段必须是完整的、可直接向候选人提出的问题
- purpose 字段是简短的标签（5-10字）
- source 字段用于区分问题来源：
  * followup: 基于当前回答的追问（显示为"追问建议"）
  * resume: 基于简历内容的问题（显示为"候选问题"）
  * job: 基于岗位要求的问题（显示为"候选问题"）

请直接返回JSON，不要包含其他内容。
"""

SIMULATE_CANDIDATE_ANSWER_PROMPT = """你现在要扮演一位正在参加面试的候选人，根据以下信息模拟回答面试官的问题。

# 候选人简历
{resume_content}

# 应聘岗位
职位: {position_title}
职位描述: {position_description}

# 候选人名字
{candidate_name}

# 候选人行为特征类型: {candidate_type}
{type_description}

# 对话历史
{conversation_history}

# 面试官当前问题
{question}

# 回答要求
1. 严格按照候选人类型的行为特征来回答
2. 回答必须基于简历中的真实信息，不要编造简历中没有的经历
3. 如果简历中没有相关经验，按类型特征处理（ideal/junior/nervous/overconfident）
4. 回答长度适中（100-300字），使用第一人称

请直接输出候选人的回答内容，不要包含任何JSON格式或其他说明。"""

FINAL_REPORT_PROMPT = """基于整场面试，生成最终评估报告。

候选人: {candidate_name}
职位: {job_title}
HR备注: {hr_notes}

## 完整问答记录
{conversation_log}

## 评分体系说明
- 每个回答从6个维度评分（技术深度、实践经验、回答具体性、逻辑清晰度、诚实度、沟通能力）
- 维度评分范围：1-4分
- 最终标准化分数：0-100分
- 评分解释：
  * 90-100分：卓越 - 远超职位要求
  * 75-89分：优秀 - 明显超出预期
  * 60-74分：良好 - 符合期望
  * 40-59分：一般 - 基本符合但有不足
  * 25-39分：较差 - 明显低于要求
  * 0-24分：不合格 - 严重不符合

## 重要评估原则
1. 追问结果权重最高：如果追问后表现下降，说明过度自信
2. 关注实际深度而非表达流畅度
3. 不要被候选人的高级术语和表面自信所迷惑

## JSON返回格式
{{
    "overall_assessment": {{
        "recommendation_score": 0-100的推荐分数,
        "recommendation": "强烈推荐/推荐/待定/不推荐",
        "summary": "100-150字的总结评价"
    }},
    "dimension_analysis": {{
        "专业能力": {{"score": 1-5, "comment": "评价"}},
        "沟通能力": {{"score": 1-5, "comment": "评价"}},
        "学习能力": {{"score": 1-5, "comment": "评价"}},
        "团队协作": {{"score": 1-5, "comment": "评价"}}
    }},
    "skill_assessment": [
        {{"skill": "技能名", "level": "水平", "evidence": "依据"}}
    ],
    "highlights": ["亮点1", "亮点2"],
    "red_flags": ["问题点1"],
    "overconfidence_detected": true或false,
    "suggested_next_steps": ["下一步建议1", "建议2"]
}}

请直接返回JSON，不要包含其他内容。"""

CANDIDATE_TYPE_DESCRIPTIONS = {
    "ideal": """理想候选人特征：
- 回答结构清晰，逻辑性强
- 有具体的项目案例和数据支撑
- 能深入解释技术原理
- 表达流畅，善于总结
- 诚实地认识自己的能力边界""",
    "junior": """初级候选人特征：
- 回答较简短，缺乏深度
- 对进阶概念不太熟悉
- 会坦诚说"这个我不太了解"或"我还在学习中"
- 态度谦虚，愿意学习
- 可能会说一些教科书式的答案""",
    "nervous": """紧张型候选人特征：
- 说话可能会结巴，如"嗯..."、"那个..."
- 用词会重复，如"就是就是"、"然后然后"
- 容易遗漏要点，回答不够完整
- 可能需要一些停顿来组织语言
- 实际能力可能比表现出来的要好""",
    "overconfident": """过度自信型候选人特征：
- 回答自信但缺乏具体细节
- 喜欢使用高级术语但解释不清
- 可能会不懂装懂，给出模糊的回答
- 使用大量不确定词汇如"一般来说"、"差不多"、"应该是"
- 缺乏对方案权衡的深入思考
- 被追问细节时可能会暴露真实水平"""
}


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

        system_prompt = "你是一位资深的面试官，擅长根据候选人简历设计针对性的面试问题。"
        user_prompt = RESUME_BASED_QUESTION_PROMPT.format(
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
        system_prompt = "你是一位资深的面试官，擅长设计能有效考察候选人能力的面试问题。"
        user_prompt = SKILL_BASED_QUESTION_PROMPT.format(
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

    async def evaluate_answer(self, question: str, answer: str, target_skills: Optional[List[str]] = None, difficulty: int = 5) -> Dict[str, Any]:
        """评估回答质量。"""
        if not answer or len(answer.strip()) < 10:
            return self._minimal_evaluation()

        system_prompt = "你是一位资深的面试评估专家，擅长客观评估候选人的回答质量，特别善于识别过度自信和不懂装懂的情况。"
        user_prompt = ANSWER_EVALUATION_PROMPT.format(
            question=question,
            answer=answer,
            target_skills=", ".join(target_skills) if target_skills else "综合能力",
            difficulty=difficulty,
        )
        try:
            return await self._llm.complete_json(system_prompt, user_prompt, temperature=0.3)
        except Exception as exc:
            logger.error("回答评估失败: {}", exc)
            return self._fallback_evaluation(answer)

    async def generate_followup_suggestions(
        self, original_question: str, answer: str, evaluation: Dict[str, Any], target_skill: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成追问建议。"""
        system_prompt = "你是一位资深的面试官，擅长设计追问问题来验证候选人的真实能力。"
        user_prompt = FOLLOWUP_SUGGESTION_PROMPT.format(
            original_question=original_question,
            answer=answer,
            evaluation_feedback=evaluation.get("feedback", ""),
            target_skill=target_skill or "综合能力",
        )
        try:
            return await self._llm.complete_json(system_prompt, user_prompt, temperature=0.6)
        except Exception as exc:
            logger.error("追问建议生成失败: {}", exc)
            return {
                "followup_suggestions": [
                    {"question": "能否提供一个具体案例细节？", "purpose": "验证经验真实性", "difficulty": 6},
                    {"question": "在此场景下的最大挑战是什么？", "purpose": "考察问题解决", "difficulty": 7},
                ],
                "hr_hint": "建议深入细节核实真实性",
            }

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

        system_prompt = "你是一位资深的面试官，擅长根据候选人的回答和简历背景设计后续问题。"
        user_prompt = CANDIDATE_QUESTIONS_PROMPT.format(
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
        type_desc = CANDIDATE_TYPE_DESCRIPTIONS.get(candidate_type, CANDIDATE_TYPE_DESCRIPTIONS["ideal"])
        user_prompt = SIMULATE_CANDIDATE_ANSWER_PROMPT.format(
            resume_content=resume_content,
            position_title=position_title,
            position_description=position_description,
            candidate_name=candidate_name,
            candidate_type=candidate_type,
            type_description=type_desc,
            conversation_history=conversation_history or "（无历史）",
            question=question,
        )
        system_prompt = "你现在扮演候选人，需给出符合设定的真实回答。"
        return await self._llm.complete(system_prompt, user_prompt, temperature=0.8)

    async def generate_final_report(self, candidate_name: str, messages: List[Dict[str, Any]], hr_notes: str = "") -> Dict[str, Any]:
        """生成最终面试报告。"""
        job_title = self.job_config.get("title", "未指定职位")
        conversation_log = self._format_conversation_log(messages)
        system_prompt = "你是一位资深的HR评估专家，擅长根据面试记录生成客观、全面的评估报告。"
        user_prompt = FINAL_REPORT_PROMPT.format(
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

    def _minimal_evaluation(self) -> Dict[str, Any]:
        """回答过短时的兜底评估。"""
        return {
            "normalized_score": 25,
            "dimension_scores": {
                "technical_depth": 1,
                "practical_experience": 1,
                "answer_specificity": 1,
                "logical_clarity": 1,
                "honesty": 2,
                "communication": 1,
            },
            "confidence_level": "uncertain",
            "should_followup": True,
            "followup_reason": "回答过短，需要追问细节",
            "feedback": "回答过短，建议追问具体案例与数据。",
        }

    def _fallback_evaluation(self, answer: str) -> Dict[str, Any]:
        """LLM 失败时的简易规则评估。"""
        length = len(answer)
        has_detail = any(kw in answer for kw in ["项目", "数据", "实现", "架构", "指标"])
        base = 50
        if length > 200 and has_detail:
            base = 70
        elif length > 100:
            base = 60
        elif length < 50:
            base = 35

        return {
            "normalized_score": base,
            "dimension_scores": {
                "technical_depth": 2,
                "practical_experience": 2,
                "answer_specificity": 2 if has_detail else 1,
                "logical_clarity": 2,
                "honesty": 3,
                "communication": 2,
            },
            "confidence_level": "uncertain",
            "should_followup": base < 65,
            "followup_reason": "建议追问以验证能力" if base < 65 else "",
            "feedback": "备用规则评估结果",
        }

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
