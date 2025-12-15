"""
简历筛选 Agent 模块

负责简历与岗位的智能匹配分析
"""
from typing import Dict, Any, Optional
from loguru import logger

from .base import BaseAgent


class ScreeningAgent(BaseAgent):
    """
    简历筛选 Agent
    
    分析简历与岗位要求的匹配度，给出评分和推荐意见
    """
    
    name = "ScreeningAgent"
    description = "简历筛选与匹配分析"
    
    system_prompt = """你是一位专业的HR招聘专家，擅长分析简历与岗位的匹配度。

你的任务是：
1. 仔细阅读岗位要求和候选人简历
2. 从多个维度评估匹配程度
3. 给出客观的评分和详细的分析报告

评估维度包括：
- 技能匹配度：必备技能和加分技能的掌握情况
- 经验匹配度：工作年限和相关经验
- 学历匹配度：学历背景是否符合要求
- 项目经验：相关项目经验的质量和深度
- 综合潜力：成长潜力和学习能力

请确保评估客观公正，给出具体的依据和建议。"""

    async def run(
        self,
        resume_content: str,
        position_requirements: Dict[str, Any],
        *,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """
        执行简历筛选分析
        
        Args:
            resume_content: 简历内容文本
            position_requirements: 岗位要求字典
            temperature: 温度参数（筛选任务建议较低）
            
        Returns:
            筛选结果字典，包含评分和分析
        """
        logger.info(f"[{self.name}] 开始筛选分析...")
        
        # 构建提示词
        prompt = f"""请分析以下简历与岗位的匹配度。

## 岗位要求
- 岗位名称：{position_requirements.get('title', '未知')}
- 岗位描述：{position_requirements.get('description', '无')}
- 必备技能：{', '.join(position_requirements.get('required_skills', []))}
- 优先技能：{', '.join(position_requirements.get('preferred_skills', []))}
- 最低经验：{position_requirements.get('min_experience', 0)} 年
- 学历要求：{', '.join(position_requirements.get('education_requirements', []))}

## 候选人简历
{resume_content}

请以 JSON 格式返回分析结果，格式如下：
{{
    "score": 85,  // 综合评分 0-100
    "recommendation": "strong",  // 推荐等级: strong/moderate/weak
    "dimension_scores": {{
        "skill_match": 80,      // 技能匹配度
        "experience_match": 85, // 经验匹配度
        "education_match": 90,  // 学历匹配度
        "project_quality": 80,  // 项目经验质量
        "potential": 85         // 综合潜力
    }},
    "highlights": ["亮点1", "亮点2"],  // 候选人亮点
    "concerns": ["不足1"],  // 需要关注的问题
    "summary": "综合评价文本"
}}"""

        result = await self.chat_json(prompt, temperature=temperature)
        
        logger.info(f"[{self.name}] 筛选完成, 评分: {result.get('score')}")
        return result
    
    async def generate_report(
        self,
        resume_content: str,
        position_requirements: Dict[str, Any],
        screening_result: Dict[str, Any],
    ) -> str:
        """
        生成详细的筛选报告（Markdown 格式）
        
        Args:
            resume_content: 简历内容
            position_requirements: 岗位要求
            screening_result: 筛选结果
            
        Returns:
            Markdown 格式的报告
        """
        prompt = f"""基于以下筛选结果，生成一份详细的 Markdown 格式筛选报告。

## 岗位信息
- 岗位：{position_requirements.get('title', '未知')}

## 筛选结果
- 综合评分：{screening_result.get('score', 0)} 分
- 推荐等级：{screening_result.get('recommendation', '未知')}
- 亮点：{screening_result.get('highlights', [])}
- 关注点：{screening_result.get('concerns', [])}

## 简历内容
{resume_content[:2000]}

请生成包含以下部分的报告：
1. 候选人基本信息概述
2. 各维度详细评估
3. 优势与不足分析
4. 面试建议（如果推荐面试）
5. 最终结论

使用清晰的 Markdown 格式，包含标题、列表等。"""

        return await self.chat(prompt, temperature=0.5)
