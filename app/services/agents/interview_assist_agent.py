"""
面试助手Agent模块。
提供基于LLM的面试问题生成、回答评估等功能。
"""
import json
import logging
from typing import Dict, List, Any, Optional
from openai import OpenAI

from .llm_config import get_config_list

logger = logging.getLogger(__name__)


# ============ 提示词模板 ============

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

请直接返回JSON，不要包含其他内容。
"""

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

请直接返回JSON，不要包含其他内容。
"""

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
- 回答模糊、使用大量不确定词汇（"一般"、"差不多"、"应该"、"可能"）
- 主动承认"记不清"、"不太熟"但仍给出笼统回答
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

请直接返回JSON，不要包含其他内容。
"""

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

请直接返回JSON，不要包含其他内容。
"""

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

请直接返回JSON，不要包含其他内容。
"""


class InterviewAssistAgent:
    """
    面试助手Agent（精简版）。
    提供基于LLM的面试问题生成、回答评估、追问建议和报告生成功能。
    """
    
    def __init__(self, job_config: Dict = None):
        """
        初始化面试助手Agent。
        
        参数:
            job_config: 职位配置
        """
        self.job_config = job_config or {}
        
        # 获取LLM配置
        llm_config = get_config_list()[0]
        self.api_key = llm_config.get('api_key', '')
        self.base_url = llm_config.get('base_url', 'https://api.openai.com/v1')
        self.model = llm_config.get('model', 'gpt-3.5-turbo')
        self.temperature = llm_config.get('temperature', 0.7)
        self.timeout = 120
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )
    
    def _call_llm(self, system_prompt: str, user_prompt: str, temperature: float = None) -> Dict:
        """
        调用LLM并返回解析后的JSON结果。
        
        参数:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数（可选）
            
        返回:
            解析后的JSON字典
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature if temperature is not None else self.temperature,
            )
            
            # 检查响应是否有效
            if not response or not response.choices:
                raise ValueError("LLM 返回空响应")
            
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("LLM 返回内容为空")
            
            result_text = content.strip()
            
            # 清理markdown代码块标记
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            elif result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            # 解析JSON
            return json.loads(result_text)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Raw response: {result_text}")
            raise ValueError(f"LLM返回的结果不是有效的JSON格式: {str(e)}")
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise ValueError(f"LLM调用失败: {str(e)}")
    
    def generate_resume_based_questions(
        self,
        resume_content: str,
        count: int = 3,
        interest_point_count: int = 2
    ) -> Dict[str, Any]:
        """
        根据简历内容生成针对性的面试问题。
        
        参数:
            resume_content: 简历文本内容
            count: 要生成的问题数量
            interest_point_count: 要生成的兴趣点数量（1-3）
            
        返回:
            包含问题和兴趣点的字典
        """
        if not resume_content:
            logger.warning("No resume content provided")
            return {"questions": [], "interest_points": []}
        
        job_title = self.job_config.get('title', '未指定职位')
        job_description = self.job_config.get('description', '')
        job_requirements = json.dumps(
            self.job_config.get('requirements', {}), 
            ensure_ascii=False, 
            indent=2
        )
        
        system_prompt = "你是一位资深的面试官，擅长根据候选人简历设计针对性的面试问题。"
        
        user_prompt = RESUME_BASED_QUESTION_PROMPT.format(
            resume_content=resume_content[:5000],  # 限制长度
            job_title=job_title,
            job_description=job_description,
            job_requirements=job_requirements,
            count=count,
            interest_point_count=interest_point_count
        )
        
        try:
            result = self._call_llm(system_prompt, user_prompt, temperature=0.7)
            
            # 处理返回的问题
            questions = []
            for q in result.get('questions', [])[:count]:
                questions.append({
                    "question": q.get("question", ""),
                    "category": q.get("category", "简历相关"),
                    "difficulty": q.get("difficulty", 6),
                    "expected_skills": q.get("expected_skills", []),
                    "source": "resume_based"
                })
            
            # 处理兴趣点（新格式：包含 content 和 question）
            interest_points = []
            for point in result.get('interest_points', [])[:interest_point_count]:
                if isinstance(point, dict):
                    interest_points.append({
                        "content": point.get('content', point.get('point', '')),
                        "question": point.get('question', '请详细介绍这方面的经验'),
                        "reason": point.get('reason', '')
                    })
                else:
                    interest_points.append({
                        "content": str(point),
                        "question": f"请详细介绍您在{str(point)}方面的经验",
                        "reason": ""
                    })
            
            return {
                "questions": questions,
                "interest_points": interest_points
            }
            
        except Exception as e:
            logger.error(f"Failed to generate resume-based questions: {e}")
            # 返回备用问题
            return self._get_fallback_resume_questions(count, interest_point_count)
    
    def _get_fallback_resume_questions(self, count: int, interest_point_count: int = 2) -> Dict[str, Any]:
        """获取备用的简历相关问题（LLM失败时使用）"""
        fallback_questions = [
            {
                "question": "请详细介绍一下您最具挑战性的项目经历",
                "category": "简历相关",
                "difficulty": 6,
                "expected_skills": ["项目经验", "问题解决"],
                "source": "resume_based"
            },
            {
                "question": "您在简历中提到的技术栈，能否举例说明实际应用场景？",
                "category": "简历相关",
                "difficulty": 5,
                "expected_skills": ["技术能力"],
                "source": "resume_based"
            },
            {
                "question": "您是如何处理项目中遇到的技术难题的？",
                "category": "简历相关",
                "difficulty": 7,
                "expected_skills": ["问题解决", "学习能力"],
                "source": "resume_based"
            }
        ]
        
        fallback_interest_points = [
            {
                "content": "项目经验",
                "question": "请详细介绍您最具代表性的项目经验",
                "reason": "验证实际工作能力"
            },
            {
                "content": "技术栈",
                "question": "请介绍您最擅长的技术栈及实际应用案例",
                "reason": "评估技术深度"
            },
            {
                "content": "团队协作",
                "question": "请描述您在团队中的角色和协作方式",
                "reason": "评估协作能力"
            }
        ]
        
        return {
            "questions": fallback_questions[:count],
            "interest_points": fallback_interest_points[:interest_point_count]
        }
    
    def generate_skill_based_questions(
        self,
        category: str,
        candidate_level: str = "senior",
        count: int = 2
    ) -> List[Dict]:
        """
        根据技能类别生成问题。
        
        参数:
            category: 问题类别（专业能力、行为面试等）
            candidate_level: 候选人经验级别
            count: 问题数量
            
        返回:
            问题字典列表
        """
        job_title = self.job_config.get('title', '未指定职位')
        
        system_prompt = "你是一位资深的面试官，擅长设计能有效考察候选人能力的面试问题。"
        
        user_prompt = SKILL_BASED_QUESTION_PROMPT.format(
            job_title=job_title,
            candidate_level=candidate_level,
            question_category=category,
            count=count
        )
        
        try:
            result = self._call_llm(system_prompt, user_prompt, temperature=0.7)
            
            questions = []
            for q in result.get('questions', [])[:count]:
                questions.append({
                    "question": q.get("question", ""),
                    "category": category,
                    "difficulty": q.get("difficulty", 6),
                    "expected_skills": q.get("expected_skills", []),
                    "source": "skill_based"
                })
            
            return questions
            
        except Exception as e:
            logger.error(f"Failed to generate skill-based questions: {e}")
            return self._get_fallback_skill_questions(category, count)
    
    def _get_fallback_skill_questions(self, category: str, count: int) -> List[Dict]:
        """获取备用的技能相关问题（LLM失败时使用）"""
        question_bank = {
            "专业能力": [
                {
                    "question": "请描述您对系统架构设计的理解",
                    "difficulty": 7,
                    "expected_skills": ["架构设计"]
                },
                {
                    "question": "您如何保证代码质量？",
                    "difficulty": 5,
                    "expected_skills": ["代码质量"]
                }
            ],
            "行为面试": [
                {
                    "question": "请描述一次您与团队成员意见不合的情况",
                    "difficulty": 6,
                    "expected_skills": ["沟通能力", "团队协作"]
                },
                {
                    "question": "您如何应对紧急的项目deadline？",
                    "difficulty": 5,
                    "expected_skills": ["压力管理"]
                }
            ]
        }
        
        questions = question_bank.get(category, question_bank["专业能力"])
        for q in questions:
            q["category"] = category
            q["source"] = "skill_based"
        
        return questions[:count]
    
    def evaluate_answer(
        self,
        question: str,
        answer: str,
        target_skills: List[str] = None,
        difficulty: int = 5
    ) -> Dict[str, Any]:
        """
        评估候选人的回答。
        
        参数:
            question: 面试问题
            answer: 候选人的回答
            target_skills: 要评估的目标技能
            difficulty: 问题难度
            
        返回:
            评估结果
        """
        if not answer or len(answer.strip()) < 10:
            return self._get_minimal_answer_evaluation()
        
        system_prompt = "你是一位资深的面试评估专家，擅长客观评估候选人的回答质量，特别善于识别过度自信和不懂装懂的情况。"
        
        user_prompt = ANSWER_EVALUATION_PROMPT.format(
            question=question,
            answer=answer,
            target_skills=", ".join(target_skills) if target_skills else "综合能力",
            difficulty=difficulty
        )
        
        try:
            result = self._call_llm(system_prompt, user_prompt, temperature=0.3)
            
            # 确保返回的数据结构完整
            evaluation = {
                "normalized_score": result.get("normalized_score", 50),
                "dimension_scores": result.get("dimension_scores", {
                    "technical_depth": 2,
                    "practical_experience": 2,
                    "answer_specificity": 2,
                    "logical_clarity": 2,
                    "honesty": 3,
                    "communication": 2
                }),
                "confidence_level": result.get("confidence_level", "uncertain"),
                "should_followup": result.get("should_followup", False),
                "followup_reason": result.get("followup_reason", ""),
                "feedback": result.get("feedback", "评估完成")
            }
            
            return evaluation
            
        except Exception as e:
            logger.error(f"Failed to evaluate answer: {e}")
            return self._get_fallback_evaluation(answer)
    
    def _get_minimal_answer_evaluation(self) -> Dict[str, Any]:
        """回答过短时的评估结果"""
        return {
            "normalized_score": 25,
            "dimension_scores": {
                "technical_depth": 1,
                "practical_experience": 1,
                "answer_specificity": 1,
                "logical_clarity": 1,
                "honesty": 2,
                "communication": 1
            },
            "confidence_level": "uncertain",
            "should_followup": True,
            "followup_reason": "回答过于简短，需要追问以获取更多信息",
            "feedback": "回答内容过少，无法进行有效评估"
        }
    
    def _get_fallback_evaluation(self, answer: str) -> Dict[str, Any]:
        """LLM失败时的备用评估"""
        # 简单的规则评估
        length = len(answer)
        has_specifics = any(kw in answer for kw in ['项目', '技术', '实现', '优化', '方案', '架构', '数据'])
        
        base_score = 50
        if length > 200 and has_specifics:
            base_score = 70
        elif length > 100:
            base_score = 60
        elif length < 50:
            base_score = 35
        
        return {
            "normalized_score": base_score,
            "dimension_scores": {
                "technical_depth": 2,
                "practical_experience": 2,
                "answer_specificity": 2 if has_specifics else 1,
                "logical_clarity": 2,
                "honesty": 3,
                "communication": 2
            },
            "confidence_level": "uncertain",
            "should_followup": base_score < 65,
            "followup_reason": "建议追问以验证能力" if base_score < 65 else "",
            "feedback": "评估完成（备用评估）"
        }
    
    def generate_followup_suggestions(
        self,
        original_question: str,
        answer: str,
        evaluation: Dict,
        target_skill: str = None
    ) -> Dict[str, Any]:
        """
        生成追问问题建议。
        
        参数:
            original_question: 原始问题
            answer: 候选人的回答
            evaluation: 回答评估
            target_skill: 要关注的技能
            
        返回:
            追问建议
        """
        system_prompt = "你是一位资深的面试官，擅长设计追问问题来验证候选人的真实能力。"
        
        user_prompt = FOLLOWUP_SUGGESTION_PROMPT.format(
            original_question=original_question,
            answer=answer,
            evaluation_feedback=evaluation.get('feedback', ''),
            target_skill=target_skill or "综合能力"
        )
        
        try:
            result = self._call_llm(system_prompt, user_prompt, temperature=0.6)
            
            return {
                "followup_suggestions": result.get("followup_suggestions", []),
                "hr_hint": result.get("hr_hint", "建议追问具体细节以验证回答的真实性")
            }
            
        except Exception as e:
            logger.error(f"Failed to generate followup suggestions: {e}")
            return self._get_fallback_followup_suggestions()
    
    def _get_fallback_followup_suggestions(self) -> Dict[str, Any]:
        """备用追问建议"""
        return {
            "followup_suggestions": [
                {
                    "question": "能否举一个具体的例子？",
                    "purpose": "验证经验真实性",
                    "difficulty": 6
                },
                {
                    "question": "您在这个过程中遇到的最大挑战是什么？",
                    "purpose": "深入了解问题解决能力",
                    "difficulty": 7
                }
            ],
            "hr_hint": "建议追问具体细节以验证回答的真实性"
        }
    
    def generate_final_report(
        self,
        candidate_name: str,
        qa_records: List[Dict],
        hr_notes: str = ""
    ) -> Dict[str, Any]:
        """
        生成最终面试报告。
        
        参数:
            candidate_name: 候选人姓名
            qa_records: QA记录列表（来自 session.qa_records JSON）
            hr_notes: HR备注
            
        返回:
            最终报告数据
        """
        job_title = self.job_config.get('title', '未指定职位')
        
        # 构建对话日志
        conversation_log = self._format_conversation_log(qa_records)
        
        system_prompt = "你是一位资深的HR评估专家，擅长根据面试记录生成客观、全面的评估报告。"
        
        user_prompt = FINAL_REPORT_PROMPT.format(
            candidate_name=candidate_name,
            job_title=job_title,
            hr_notes=hr_notes or "无",
            conversation_log=conversation_log
        )
        
        try:
            result = self._call_llm(system_prompt, user_prompt, temperature=0.4)
            
            # 确保返回完整的报告结构
            report = {
                "overall_assessment": result.get("overall_assessment", {
                    "recommendation_score": 50,
                    "recommendation": "待定",
                    "summary": f"候选人{candidate_name}完成了面试。"
                }),
                "dimension_analysis": result.get("dimension_analysis", {}),
                "skill_assessment": result.get("skill_assessment", []),
                "highlights": result.get("highlights", []),
                "red_flags": result.get("red_flags", []),
                "overconfidence_detected": result.get("overconfidence_detected", False),
                "suggested_next_steps": result.get("suggested_next_steps", [])
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate final report: {e}")
            return self._get_fallback_report(candidate_name, qa_records)
    
    def _format_conversation_log(self, qa_records: List[Dict]) -> str:
        """格式化对话日志（适配新的 JSON 格式）"""
        lines = []
        for qa in qa_records:
            if qa is None:
                continue
            round_num = qa.get('round', 0)
            question = qa.get('question', '')
            answer = qa.get('answer', '')
            evaluation = qa.get('evaluation', {})
            score = evaluation.get('normalized_score', 0) if evaluation else 0
            confidence = evaluation.get('confidence_level', 'unknown') if evaluation else 'unknown'
            
            lines.append(f"### 第{round_num}轮")
            lines.append(f"**问题**: {question}")
            lines.append(f"**回答**: {answer}")
            lines.append(f"**评分**: {score}/100 (信心程度: {confidence})")
            lines.append("")
        
        return "\n".join(lines)
    
    def generate_candidate_questions(
        self,
        current_question: str,
        current_answer: str,
        conversation_history: List[Dict] = None,
        resume_summary: str = "",
        followup_count: int = 2,
        alternative_count: int = 3
    ) -> List[Dict[str, Any]]:
        """
        根据面试上下文生成候选提问。
        
        参数:
            current_question: 当前问题
            current_answer: 候选人当前回答
            conversation_history: 历史对话记录
            resume_summary: 简历摘要
            followup_count: 追问问题数量
            alternative_count: 候选问题数量
            
        返回:
            候选问题列表
        """
        job_title = self.job_config.get('title', '未指定职位')
        job_requirements = json.dumps(
            self.job_config.get('requirements', {}),
            ensure_ascii=False,
            indent=2
        )
        
        # 格式化历史对话
        history_text = ""
        if conversation_history:
            for i, qa in enumerate(conversation_history, 1):
                history_text += f"第{i}轮:\n"
                history_text += f"  问: {qa.get('question', '')}\n"
                history_text += f"  答: {qa.get('answer', '')}\n\n"
        else:
            history_text = "（这是第一个问题）"
        
        system_prompt = "你是一位资深的面试官，擅长根据候选人的回答和简历背景，设计有针对性的后续问题。"
        
        total_count = followup_count + alternative_count
        user_prompt = CANDIDATE_QUESTIONS_PROMPT.format(
            job_title=job_title,
            job_requirements=job_requirements,
            resume_summary=resume_summary or "（未提供简历摘要）",
            conversation_history=history_text,
            current_question=current_question,
            current_answer=current_answer,
            followup_count=followup_count,
            alternative_count=alternative_count
        )
        
        try:
            result = self._call_llm(system_prompt, user_prompt, temperature=0.7)
            
            questions = []
            for q in result.get('candidate_questions', [])[:total_count]:
                questions.append({
                    "question": q.get("question", ""),
                    "purpose": q.get("purpose", ""),
                    "expected_skills": q.get("expected_skills", []),
                    "source": q.get("source", "followup")
                })
            
            return questions
            
        except Exception as e:
            logger.error(f"Failed to generate candidate questions: {e}")
            return self._get_fallback_candidate_questions(current_answer)
    
    def _get_fallback_candidate_questions(self, answer: str) -> List[Dict[str, Any]]:
        """备用候选问题（LLM失败时使用）"""
        return [
            {
                "question": "能否举一个具体的例子来说明？",
                "purpose": "验证经验真实性",
                "expected_skills": ["实践经验"],
                "source": "followup"
            },
            {
                "question": "在这个过程中遇到的最大挑战是什么？",
                "purpose": "考察问题解决能力",
                "expected_skills": ["问题解决"],
                "source": "followup"
            },
            {
                "question": "如果重新做这个决定，您会有什么不同的选择？",
                "purpose": "考察反思能力",
                "expected_skills": ["反思能力"],
                "source": "followup"
            }
        ]

    def _get_fallback_report(self, candidate_name: str, qa_records: List[Dict]) -> Dict[str, Any]:
        """备用报告生成"""
        # 计算平均分（过滤掉 None 值）
        scores = [
            qa.get('evaluation', {}).get('normalized_score', 50)
            for qa in qa_records
            if qa is not None
        ]
        avg_score = sum(scores) / len(scores) if scores else 50
        
        # 确定推荐意见
        if avg_score >= 75:
            recommendation = "推荐"
        elif avg_score >= 60:
            recommendation = "待定"
        else:
            recommendation = "不推荐"
        
        return {
            "overall_assessment": {
                "recommendation_score": round(avg_score, 1),
                "recommendation": recommendation,
                "summary": f"候选人{candidate_name}在面试中表现{'良好' if avg_score >= 60 else '一般'}。"
            },
            "dimension_analysis": {
                "专业能力": {"score": 3, "comment": "待评估"},
                "沟通能力": {"score": 3, "comment": "待评估"},
                "学习能力": {"score": 3, "comment": "待评估"},
                "团队协作": {"score": 3, "comment": "待评估"}
            },
            "skill_assessment": [],
            "highlights": [],
            "red_flags": [],
            "overconfidence_detected": False,
            "suggested_next_steps": ["需要进一步评估"]
        }


# 单例实例
_interview_assist_agent = None


def get_interview_assist_agent(job_config: Dict = None) -> InterviewAssistAgent:
    """
    获取InterviewAssistAgent实例。
    
    注意：如果传入新的配置，会创建新实例。
    """
    global _interview_assist_agent
    
    if job_config:
        # 如果有新配置，创建新实例
        return InterviewAssistAgent(job_config=job_config)
    
    if _interview_assist_agent is None:
        _interview_assist_agent = InterviewAssistAgent()
    
    return _interview_assist_agent
