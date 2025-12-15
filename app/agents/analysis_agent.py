"""
综合分析 Agent 模块

负责整合多维度数据进行候选人综合评估
"""
from typing import Dict, Any, List, Optional
from loguru import logger

from .base import BaseAgent


class AnalysisAgent(BaseAgent):
    """
    综合分析 Agent
    
    整合简历筛选、视频分析、面试记录等多维度数据，
    基于 Rubric 量表给出最终评估和录用建议
    """
    
    name = "AnalysisAgent"
    description = "候选人综合评估与录用建议"
    
    system_prompt = """你是一位资深的人力资源顾问，擅长综合评估候选人。

你的任务是整合以下数据源进行综合分析：
1. 简历筛选结果：技能匹配度、经验评估
2. 视频分析结果：大五人格特质、表达能力
3. 面试记录：问答表现、专业深度
4. 岗位要求：核心需求、团队文化

评估维度（Rubric 量表）：
- 专业能力（30%）：技术深度、项目经验、问题解决
- 学习潜力（20%）：成长空间、学习能力、适应性
- 沟通协作（20%）：表达清晰、团队协作、人际交往
- 文化适配（15%）：价值观、工作风格、稳定性
- 综合素质（15%）：领导力、主动性、责任心

推荐等级：
- strongly_recommended：强烈推荐，建议优先录用
- recommended：推荐，可以进入下一轮或录用
- conditional：有条件推荐，需关注特定问题
- not_recommended：不推荐，与岗位匹配度较低

请给出专业、客观、全面的评估意见。"""

    # Rubric 权重配置
    RUBRIC_WEIGHTS = {
        "professional_ability": 0.30,   # 专业能力
        "learning_potential": 0.20,     # 学习潜力
        "communication": 0.20,          # 沟通协作
        "cultural_fit": 0.15,           # 文化适配
        "overall_quality": 0.15,        # 综合素质
    }

    async def run(
        self,
        position_info: Dict[str, Any],
        resume_info: Dict[str, Any],
        screening_result: Optional[Dict[str, Any]] = None,
        video_analysis: Optional[Dict[str, Any]] = None,
        interview_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        执行综合分析
        
        Args:
            position_info: 岗位信息
            resume_info: 简历信息
            screening_result: 筛选结果（可选）
            video_analysis: 视频分析结果（可选）
            interview_result: 面试结果（可选）
            
        Returns:
            综合分析结果字典
        """
        logger.info(f"[{self.name}] 开始综合分析...")
        
        # 构建输入数据描述
        input_sections = []
        
        # 岗位信息
        input_sections.append(f"""## 岗位信息
- 岗位名称：{position_info.get('title', '未知')}
- 部门：{position_info.get('department', '未知')}
- 必备技能：{', '.join(position_info.get('required_skills', []))}
- 经验要求：{position_info.get('min_experience', 0)} 年""")
        
        # 简历信息
        input_sections.append(f"""## 候选人简历
- 姓名：{resume_info.get('candidate_name', '未知')}
- 简历摘要：{resume_info.get('content', '')[:1000]}""")
        
        # 筛选结果
        if screening_result:
            input_sections.append(f"""## 简历筛选结果
- 综合评分：{screening_result.get('score', 'N/A')}
- 推荐等级：{screening_result.get('recommendation', 'N/A')}
- 亮点：{screening_result.get('highlights', [])}
- 关注点：{screening_result.get('concerns', [])}""")
        
        # 视频分析
        if video_analysis:
            big_five = video_analysis.get('big_five_scores', {})
            input_sections.append(f"""## 视频分析结果
- 开放性：{big_five.get('openness', 'N/A')}
- 尽责性：{big_five.get('conscientiousness', 'N/A')}
- 外向性：{big_five.get('extraversion', 'N/A')}
- 宜人性：{big_five.get('agreeableness', 'N/A')}
- 神经质：{big_five.get('neuroticism', 'N/A')}
- 分析摘要：{video_analysis.get('summary', 'N/A')}""")
        
        # 面试结果
        if interview_result:
            input_sections.append(f"""## 面试评估结果
- 最终评分：{interview_result.get('final_score', 'N/A')}
- 总体评价：{interview_result.get('overall_evaluation', 'N/A')}
- 建议：{interview_result.get('recommendation', 'N/A')}""")
        
        prompt = f"""{chr(10).join(input_sections)}

---

请基于以上信息进行综合分析，以 JSON 格式返回：
{{
    "final_score": 85,  // 综合得分 0-100
    "recommendation_level": "recommended",  // strongly_recommended/recommended/conditional/not_recommended
    "recommendation_reason": "推荐理由详细说明",
    "suggested_action": "建议的下一步行动",
    "dimension_scores": {{
        "professional_ability": {{
            "score": 85,
            "weight": 0.30,
            "comment": "专业能力评价"
        }},
        "learning_potential": {{
            "score": 80,
            "weight": 0.20,
            "comment": "学习潜力评价"
        }},
        "communication": {{
            "score": 85,
            "weight": 0.20,
            "comment": "沟通协作评价"
        }},
        "cultural_fit": {{
            "score": 80,
            "weight": 0.15,
            "comment": "文化适配评价"
        }},
        "overall_quality": {{
            "score": 82,
            "weight": 0.15,
            "comment": "综合素质评价"
        }}
    }},
    "strengths": ["优势1", "优势2"],
    "concerns": ["关注点1"],
    "risk_factors": ["潜在风险"],
    "development_suggestions": ["发展建议"]
}}"""

        result = await self.chat_json(prompt, temperature=0.3)
        
        # 添加输入快照
        result["input_snapshot"] = {
            "position": position_info.get("title"),
            "candidate": resume_info.get("candidate_name"),
            "has_screening": screening_result is not None,
            "has_video": video_analysis is not None,
            "has_interview": interview_result is not None,
        }
        
        logger.info(
            f"[{self.name}] 分析完成: {result.get('recommendation_level')}, "
            f"评分: {result.get('final_score')}"
        )
        return result
    
    async def generate_report(
        self,
        analysis_result: Dict[str, Any],
        include_details: bool = True,
    ) -> str:
        """
        生成综合分析报告（Markdown 格式）
        
        Args:
            analysis_result: 综合分析结果
            include_details: 是否包含详细维度分析
            
        Returns:
            Markdown 格式报告
        """
        prompt = f"""将以下综合分析结果转换为专业的 Markdown 格式报告。

分析结果：
{analysis_result}

要求：
1. 专业的报告格式，适合HR审阅
2. 清晰的标题层级
3. 使用表格展示维度评分
4. 重点突出推荐等级和理由
5. 包含明确的行动建议
{"6. 包含各维度的详细分析" if include_details else ""}"""

        return await self.chat(prompt, temperature=0.5)
    
    async def compare_candidates(
        self,
        candidates: List[Dict[str, Any]],
        position_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        多候选人对比分析
        
        Args:
            candidates: 候选人分析结果列表
            position_info: 岗位信息
            
        Returns:
            对比分析结果
        """
        logger.info(f"[{self.name}] 对比 {len(candidates)} 位候选人...")
        
        candidates_desc = "\n\n".join([
            f"### 候选人 {i+1}: {c.get('candidate_name', '未知')}\n"
            f"- 综合评分：{c.get('final_score', 'N/A')}\n"
            f"- 推荐等级：{c.get('recommendation_level', 'N/A')}\n"
            f"- 优势：{c.get('strengths', [])}\n"
            f"- 关注点：{c.get('concerns', [])}"
            for i, c in enumerate(candidates)
        ])
        
        prompt = f"""请对比以下候选人，为岗位「{position_info.get('title', '未知')}」给出排名和建议。

{candidates_desc}

请以 JSON 格式返回对比结果：
{{
    "ranking": [
        {{"rank": 1, "candidate_name": "姓名", "reason": "排名理由"}}
    ],
    "comparison_summary": "对比总结",
    "final_recommendation": "最终建议"
}}"""

        return await self.chat_json(prompt, temperature=0.3)
