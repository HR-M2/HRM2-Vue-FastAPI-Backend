"""
面试辅助 Agent 模块

负责生成面试问题、评估回答、生成面试报告
"""
from typing import Dict, Any, List, Optional
from loguru import logger

from .base import BaseAgent


class InterviewAgent(BaseAgent):
    """
    面试辅助 Agent
    
    功能：
    - 根据岗位和简历生成面试问题
    - 评估候选人回答
    - 生成下一轮追问建议
    - 生成面试报告
    """
    
    name = "InterviewAgent"
    description = "面试问题生成与回答评估"
    
    system_prompt = """你是一位资深的面试官，擅长设计面试问题和评估候选人。

你的职责：
1. 根据岗位要求和候选人背景设计针对性问题
2. 客观评估候选人的回答质量
3. 提供专业的面试建议和追问方向
4. 最终给出全面的面试评估

面试问题类型：
- 技术能力：考察专业知识和技能
- 项目经验：深入了解过往项目
- 情景模拟：考察问题解决能力
- 行为面试：了解工作风格和价值观
- 开放讨论：考察思维深度和广度

请确保问题专业、有针对性，评估客观公正。"""

    async def run(
        self,
        resume_content: str,
        position_requirements: Dict[str, Any],
        interview_type: str = "general",
        *,
        count: int = 5,
        difficulty: str = "medium",
        focus_areas: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        生成面试问题
        
        Args:
            resume_content: 简历内容
            position_requirements: 岗位要求
            interview_type: 面试类型 general/technical/behavioral
            count: 问题数量
            difficulty: 难度 easy/medium/hard
            focus_areas: 关注领域列表
            
        Returns:
            包含问题列表的字典
        """
        logger.info(f"[{self.name}] 生成 {interview_type} 面试问题...")
        
        type_desc = {
            "general": "综合面试，覆盖技术、项目、行为等多方面",
            "technical": "技术面试，重点考察专业技能和技术深度",
            "behavioral": "行为面试，考察工作风格、团队协作和价值观",
        }.get(interview_type, "综合面试")
        
        prompt = f"""请为以下候选人生成面试问题。

## 面试类型
{type_desc}

## 岗位要求
- 岗位：{position_requirements.get('title', '未知')}
- 必备技能：{', '.join(position_requirements.get('required_skills', []))}
- 经验要求：{position_requirements.get('min_experience', 0)} 年

## 候选人简历摘要
{resume_content[:1500]}

## 生成要求
- 数量：{count} 个问题
- 难度：{difficulty}
- 关注领域：{', '.join(focus_areas) if focus_areas else '不限'}

请以 JSON 格式返回：
{{
    "questions": [
        {{
            "id": 1,
            "question": "问题内容",
            "type": "technical/behavioral/situational/experience",
            "difficulty": "easy/medium/hard",
            "purpose": "考察目的",
            "expected_points": ["期望答案要点1", "要点2"]
        }}
    ],
    "interview_tips": "面试建议"
}}"""

        result = await self.chat_json(prompt, temperature=0.7)
        logger.info(f"[{self.name}] 生成 {len(result.get('questions', []))} 个问题")
        return result
    
    async def evaluate_answer(
        self,
        question: str,
        answer: str,
        expected_points: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        评估候选人回答
        
        Args:
            question: 面试问题
            answer: 候选人回答
            expected_points: 期望答案要点
            
        Returns:
            评估结果字典
        """
        logger.info(f"[{self.name}] 评估回答...")
        
        prompt = f"""请评估候选人的面试回答。

## 问题
{question}

## 候选人回答
{answer}

## 参考评分要点
{', '.join(expected_points) if expected_points else '无特定要求'}

请以 JSON 格式返回评估结果：
{{
    "score": 85,  // 0-100 评分
    "evaluation": "评价内容",
    "strengths": ["回答亮点"],
    "weaknesses": ["不足之处"],
    "follow_up_questions": ["建议追问的问题"]
}}"""

        return await self.chat_json(prompt, temperature=0.3)
    
    async def generate_report(
        self,
        position_title: str,
        candidate_name: str,
        qa_records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        生成面试报告
        
        Args:
            position_title: 岗位名称
            candidate_name: 候选人姓名
            qa_records: 问答记录列表
            
        Returns:
            面试报告字典
        """
        logger.info(f"[{self.name}] 生成面试报告...")
        
        # 格式化问答记录
        qa_text = "\n".join([
            f"Q{i+1}: {r.get('question', '')}\nA{i+1}: {r.get('answer', '')}\n评分: {r.get('score', 'N/A')}"
            for i, r in enumerate(qa_records)
        ])
        
        prompt = f"""请根据面试记录生成综合报告。

## 基本信息
- 应聘岗位：{position_title}
- 候选人：{candidate_name}
- 面试轮数：{len(qa_records)}

## 问答记录
{qa_text}

请以 JSON 格式返回面试报告：
{{
    "final_score": 85,  // 综合评分
    "overall_evaluation": "总体评价",
    "technical_ability": {{
        "score": 80,
        "comment": "技术能力评价"
    }},
    "communication_skill": {{
        "score": 85,
        "comment": "沟通表达评价"
    }},
    "problem_solving": {{
        "score": 80,
        "comment": "问题解决能力"
    }},
    "cultural_fit": {{
        "score": 85,
        "comment": "文化适配度"
    }},
    "recommendation": "hire/hold/reject",
    "recommendation_reason": "推荐理由",
    "suggested_next_steps": ["建议后续步骤"]
}}"""

        result = await self.chat_json(prompt, temperature=0.3)
        
        # 生成 Markdown 报告
        result["markdown_report"] = await self._generate_markdown_report(
            position_title, candidate_name, qa_records, result
        )
        
        return result
    
    async def _generate_markdown_report(
        self,
        position_title: str,
        candidate_name: str,
        qa_records: List[Dict[str, Any]],
        evaluation: Dict[str, Any],
    ) -> str:
        """生成 Markdown 格式报告"""
        prompt = f"""将以下面试评估结果转换为专业的 Markdown 格式报告。

岗位：{position_title}
候选人：{candidate_name}
评估结果：{evaluation}

要求：
1. 包含清晰的标题结构
2. 使用表格展示评分
3. 分点列出优缺点
4. 给出明确的结论和建议"""

        return await self.chat(prompt, temperature=0.5)
