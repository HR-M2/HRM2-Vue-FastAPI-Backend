"""单人综合分析评估代理模块。

基于 Rubric 量表的多维度评估系统，整合：
- 简历内容
- 简历初筛报告
- 沉浸式面试会话记录（含心理评分）

生成最终的综合录用建议，包含：
- 五维度评估（专业能力、工作经验、软技能、文化匹配、面试表现）
- 心理分析（大五人格、可信度分析、抑郁风险评估）
"""
import json
import logging
from typing import Dict, Any, List, Optional

from .llm_client import get_llm_client

logger = logging.getLogger(__name__)


# ============ Rubric 量表定义 ============

RUBRIC_SCALES = {
    5: {"label": "卓越", "description": "远超岗位要求，表现突出"},
    4: {"label": "优秀", "description": "超出岗位要求，表现良好"},
    3: {"label": "良好", "description": "符合岗位要求，表现合格"},
    2: {"label": "一般", "description": "基本符合，但有提升空间"},
    1: {"label": "不足", "description": "未达到岗位要求"}
}

# 评估维度定义
EVALUATION_DIMENSIONS = {
    "professional_competency": {
        "name": "专业能力",
        "weight": 0.30,
        "description": "专业技能、知识深度、技术能力",
        "sub_dimensions": [
            "核心技能掌握程度",
            "专业知识深度",
            "问题解决能力",
            "学习成长潜力"
        ]
    },
    "work_experience": {
        "name": "工作经验",
        "weight": 0.25,
        "description": "相关经验、项目经历、成果业绩",
        "sub_dimensions": [
            "经验相关性",
            "项目复杂度",
            "成果可量化性",
            "职责承担程度"
        ]
    },
    "soft_skills": {
        "name": "软技能",
        "weight": 0.20,
        "description": "沟通协作、团队合作、抗压能力",
        "sub_dimensions": [
            "沟通表达能力",
            "团队协作意识",
            "压力应对能力",
            "主动性与责任心"
        ]
    },
    "cultural_fit": {
        "name": "文化匹配",
        "weight": 0.15,
        "description": "价值观契合、职业态度、发展意愿",
        "sub_dimensions": [
            "职业价值观",
            "工作态度",
            "发展意愿",
            "稳定性预期"
        ]
    },
    "interview_performance": {
        "name": "面试表现",
        "weight": 0.10,
        "description": "面试中的回答质量、逻辑思维、应变能力",
        "sub_dimensions": [
            "回答逻辑性",
            "思维深度",
            "应变能力",
            "自我认知准确性"
        ]
    }
}

# 推荐等级定义
RECOMMENDATION_LEVELS = {
    "strong_recommend": {"min_score": 85, "label": "强烈推荐", "action": "建议优先录用，尽快安排后续流程"},
    "recommend": {"min_score": 70, "label": "推荐录用", "action": "符合要求，可以录用"},
    "cautious": {"min_score": 55, "label": "谨慎考虑", "action": "存在一定风险，建议进一步评估"},
    "not_recommend": {"min_score": 0, "label": "不推荐", "action": "不建议录用"}
}


class CandidateComprehensiveAnalyzer:
    """
    单人综合分析评估器。
    
    使用多视角 LLM 评估，基于 Rubric 量表打分，
    生成全面的录用建议报告。
    """
    
    def __init__(self, job_config: Dict[str, Any] = None):
        """
        初始化分析器。
        
        参数:
            job_config: 岗位配置信息
        """
        self.job_config = job_config or {}
        self._llm = get_llm_client()
    
    async def analyze(
        self,
        candidate_name: str,
        resume_content: str,
        screening_report: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        执行综合分析。
        
        参数:
            candidate_name: 候选人姓名
            resume_content: 简历内容
            screening_report: 简历初筛报告
            conversation_history: 沉浸式面试会话记录，格式：
                [{
                    "speaker": "interviewer"/"candidate",
                    "text": "发言内容",
                    "timestamp": "时间",
                    "candidate_scores": {
                        "big_five": {...},
                        "deception": {...},
                        "depression": {...}
                    }
                }]
            progress_callback: 进度回调函数
            
        返回:
            综合分析结果（含心理分析）
        """
        
        def update_progress(step: str, percent: int):
            if progress_callback:
                progress_callback(step, percent)
        
        update_progress("准备数据", 5)
        
        # 1. 构建候选人完整画像
        candidate_profile = self._build_candidate_profile(
            candidate_name=candidate_name,
            resume_content=resume_content,
            screening_report=screening_report,
            conversation_history=conversation_history
        )
        
        update_progress("专业能力评估", 20)
        
        # 2. 多维度评估
        dimension_scores = {}
        
        # 专业能力评估
        dimension_scores["professional_competency"] = await self._evaluate_dimension(
            "professional_competency",
            candidate_profile,
            EVALUATION_DIMENSIONS["professional_competency"]
        )
        update_progress("工作经验评估", 35)
        
        # 工作经验评估
        dimension_scores["work_experience"] = await self._evaluate_dimension(
            "work_experience",
            candidate_profile,
            EVALUATION_DIMENSIONS["work_experience"]
        )
        update_progress("软技能评估", 50)
        
        # 软技能评估
        dimension_scores["soft_skills"] = await self._evaluate_dimension(
            "soft_skills",
            candidate_profile,
            EVALUATION_DIMENSIONS["soft_skills"]
        )
        update_progress("文化匹配评估", 65)
        
        # 文化匹配评估
        dimension_scores["cultural_fit"] = await self._evaluate_dimension(
            "cultural_fit",
            candidate_profile,
            EVALUATION_DIMENSIONS["cultural_fit"]
        )
        update_progress("面试表现评估", 80)
        
        # 面试表现评估
        dimension_scores["interview_performance"] = await self._evaluate_dimension(
            "interview_performance",
            candidate_profile,
            EVALUATION_DIMENSIONS["interview_performance"]
        )
        update_progress("心理分析", 85)
        
        # 3. 心理分析（从 conversation_history 提取心理评分并分析）
        psychological_data = self._extract_psychological_scores(conversation_history)
        
        # 大五人格分析（由 AI 综合判断）
        avg_big_five = self._calculate_avg_big_five(psychological_data['big_five_scores'])
        big_five_analysis = await self._analyze_big_five(avg_big_five)
        
        # 可信度分析
        credibility_analysis = await self._analyze_credibility(psychological_data['deception_scores'])
        
        # 抑郁风险评估
        depression_analysis = self._analyze_depression(psychological_data['depression_scores'])
        
        psychological_analysis = {
            'big_five': big_five_analysis,
            'credibility': credibility_analysis,
            'depression': depression_analysis
        }
        
        update_progress("生成综合报告", 92)
        
        # 4. 计算综合得分
        final_score = self._calculate_final_score(dimension_scores)
        
        # 5. 确定推荐等级
        recommendation = self._determine_recommendation(final_score)
        
        # 6. 生成综合报告（含心理分析）
        comprehensive_report = await self._generate_comprehensive_report(
            candidate_name=candidate_name,
            candidate_profile=candidate_profile,
            dimension_scores=dimension_scores,
            psychological_analysis=psychological_analysis,
            final_score=final_score,
            recommendation=recommendation
        )
        
        update_progress("完成", 100)
        
        return {
            "candidate_name": candidate_name,
            "final_score": final_score,
            "recommendation": recommendation,
            "dimension_scores": dimension_scores,
            "psychological_analysis": psychological_analysis,
            "comprehensive_report": comprehensive_report,
            "rubric_scales": RUBRIC_SCALES,
            "evaluation_dimensions": EVALUATION_DIMENSIONS
        }
    
    def _build_candidate_profile(
        self,
        candidate_name: str,
        resume_content: str,
        screening_report: Dict,
        conversation_history: List[Dict]
    ) -> str:
        """构建候选人完整画像文本（用于维度评估）。"""
        
        profile_parts = []
        
        # 基本信息
        profile_parts.append(f"# 候选人：{candidate_name}")
        profile_parts.append(f"## 应聘岗位：{self.job_config.get('title', '未指定')}")
        
        # 简历内容
        profile_parts.append("\n## 一、简历内容")
        profile_parts.append(resume_content[:3000] if resume_content else "无简历内容")
        
        # 简历初筛报告
        profile_parts.append("\n## 二、简历初筛报告")
        if screening_report:
            score = screening_report.get('comprehensive_score', 'N/A')
            summary = screening_report.get('summary', screening_report.get('screening_summary', ''))
            profile_parts.append(f"初筛评分：{score}")
            profile_parts.append(f"初筛摘要：{summary}")
        else:
            profile_parts.append("无初筛报告")
        
        # 沉浸式面试会话记录
        profile_parts.append("\n## 三、沉浸式面试会话记录")
        if conversation_history:
            for utterance in conversation_history:
                speaker = utterance.get('speaker', '')
                text = utterance.get('text', '')
                speaker_label = '面试官' if speaker == 'interviewer' else '候选人'
                profile_parts.append(f"**{speaker_label}**：{text}")
        else:
            profile_parts.append("无面试记录")
        
        return "\n".join(profile_parts)
    
    def _extract_psychological_scores(
        self,
        conversation_history: List[Dict]
    ) -> Dict[str, Any]:
        """从会话历史中提取心理评分数据。"""
        
        big_five_scores = []
        deception_scores = []
        depression_scores = []
        
        for utterance in conversation_history:
            scores = utterance.get('candidate_scores', {})
            if not scores:
                continue
            
            # 提取大五人格
            if scores.get('big_five'):
                big_five_scores.append({
                    'text': utterance.get('text', ''),
                    'speaker': utterance.get('speaker', ''),
                    'scores': scores['big_five']
                })
            
            # 提取欺骗检测
            if scores.get('deception'):
                deception_scores.append({
                    'text': utterance.get('text', ''),
                    'speaker': utterance.get('speaker', ''),
                    'score': scores['deception'].get('score', 0),
                    'confidence': scores['deception'].get('confidence', 0)
                })
            
            # 提取抑郁风险
            if scores.get('depression'):
                depression_scores.append({
                    'text': utterance.get('text', ''),
                    'speaker': utterance.get('speaker', ''),
                    'score': scores['depression'].get('score', 0),
                    'level': scores['depression'].get('level', 'low'),
                    'confidence': scores['depression'].get('confidence', 0)
                })
        
        return {
            'big_five_scores': big_five_scores,
            'deception_scores': deception_scores,
            'depression_scores': depression_scores
        }
    
    def _calculate_avg_big_five(self, big_five_scores: List[Dict]) -> Dict[str, float]:
        """计算大五人格各维度平均值。"""
        if not big_five_scores:
            return {
                'openness': 0.5,
                'conscientiousness': 0.5,
                'extraversion': 0.5,
                'agreeableness': 0.5,
                'neuroticism': 0.5
            }
        
        totals = {'openness': 0, 'conscientiousness': 0, 'extraversion': 0, 
                  'agreeableness': 0, 'neuroticism': 0}
        count = len(big_five_scores)
        
        for item in big_five_scores:
            scores = item.get('scores', {})
            for key in totals:
                totals[key] += scores.get(key, 0.5)
        
        return {k: round(v / count, 3) for k, v in totals.items()}
    
    async def _analyze_big_five(
        self,
        avg_scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """分析大五人格，由 AI 综合判断候选人性格特征。"""
        
        system_prompt = """你是一位专业的心理分析师，擅长基于大五人格模型分析候选人的性格特征。

大五人格各维度说明：
- openness（开放性）：对新经验、创意和抽象思维的接受程度
- conscientiousness（尽责性）：做事的条理性、责任心和自律程度
- extraversion（外向性）：社交活跃度、精力充沛程度
- agreeableness（宜人性）：合作性、同理心和信任他人的倾向
- neuroticism（神经质）：情绪稳定性，越高表示越容易焦虑、紧张

评分范围：0-1，0.5 为中等水平

请根据五个维度的评分，综合分析候选人的性格特征，给出专业、客观的分析。"""

        user_prompt = f"""请分析以下候选人的大五人格评分：

- 开放性 (openness): {avg_scores.get('openness', 0.5)}
- 尽责性 (conscientiousness): {avg_scores.get('conscientiousness', 0.5)}
- 外向性 (extraversion): {avg_scores.get('extraversion', 0.5)}
- 宜人性 (agreeableness): {avg_scores.get('agreeableness', 0.5)}
- 神经质 (neuroticism): {avg_scores.get('neuroticism', 0.5)}

请输出 JSON 格式：
{{
    "personality_summary": "一句话概括候选人性格特点",
    "strengths": ["性格优势1", "性格优势2"],
    "potential_concerns": ["潜在关注点1"],
    "work_style": "工作风格描述",
    "team_fit": "团队协作倾向",
    "detailed_analysis": "详细分析（100-200字）"
}}"""

        try:
            result = await self._llm.complete_json(system_prompt, user_prompt, temperature=0.4)
            result['scores'] = avg_scores
            return result
        except Exception as e:
            logger.error(f"大五人格分析失败: {e}")
            return {
                'scores': avg_scores,
                'personality_summary': '无法完成性格分析',
                'strengths': [],
                'potential_concerns': [],
                'work_style': '未知',
                'team_fit': '未知',
                'detailed_analysis': f'分析过程出现异常：{str(e)}'
            }
    
    async def _analyze_credibility(
        self,
        deception_scores: List[Dict]
    ) -> Dict[str, Any]:
        """分析面试可信度，识别低可信度和高可信度回答。"""
        
        if not deception_scores:
            return {
                'overall_score': 1.0,
                'level': '高可信度',
                'low_credibility_responses': [],
                'high_credibility_responses': [],
                'analysis': '无欺骗检测数据'
            }
        
        # 计算整体可信度（1 - 平均欺骗分数）
        total_deception = sum(item.get('score', 0) for item in deception_scores)
        avg_deception = total_deception / len(deception_scores)
        overall_credibility = round(1 - avg_deception, 3)
        
        # 确定可信度等级
        if overall_credibility >= 0.8:
            level = '高可信度'
        elif overall_credibility >= 0.6:
            level = '中等可信度'
        else:
            level = '低可信度'
        
        # 找出低可信度回答（欺骗分数 > 0.5）
        low_credibility = [
            {
                'text': item['text'][:100] + '...' if len(item.get('text', '')) > 100 else item.get('text', ''),
                'deception_score': item.get('score', 0),
                'confidence': item.get('confidence', 0)
            }
            for item in deception_scores
            if item.get('score', 0) > 0.5 and item.get('speaker') == 'candidate'
        ]
        
        # 找出高可信度回答（欺骗分数 < 0.2）
        high_credibility = [
            {
                'text': item['text'][:100] + '...' if len(item.get('text', '')) > 100 else item.get('text', ''),
                'deception_score': item.get('score', 0),
                'confidence': item.get('confidence', 0)
            }
            for item in deception_scores
            if item.get('score', 0) < 0.2 and item.get('speaker') == 'candidate'
        ]
        
        # 限制数量
        low_credibility = sorted(low_credibility, key=lambda x: -x['deception_score'])[:5]
        high_credibility = sorted(high_credibility, key=lambda x: x['deception_score'])[:5]
        
        # 生成分析
        analysis = f"面试整体可信度为 {overall_credibility:.1%}，属于{level}。"
        if low_credibility:
            analysis += f"发现 {len(low_credibility)} 处可能存在夸大或不实陈述的回答，建议在后续沟通中进一步核实。"
        else:
            analysis += "未发现明显的不可信回答，候选人陈述整体可信。"
        
        return {
            'overall_score': overall_credibility,
            'level': level,
            'low_credibility_responses': low_credibility,
            'high_credibility_responses': high_credibility,
            'analysis': analysis
        }
    
    def _analyze_depression(
        self,
        depression_scores: List[Dict]
    ) -> Dict[str, Any]:
        """分析抑郁风险，给出总体评估。"""
        
        if not depression_scores:
            return {
                'overall_score': 0,
                'level': 'low',
                'level_label': '低风险',
                'interpretation': '无抑郁检测数据'
            }
        
        # 计算平均抑郁分数
        total_score = sum(item.get('score', 0) for item in depression_scores)
        avg_score = round(total_score / len(depression_scores), 1)
        
        # 统计各等级出现次数
        level_counts = {'low': 0, 'medium': 0, 'high': 0}
        for item in depression_scores:
            level = item.get('level', 'low')
            if level in level_counts:
                level_counts[level] += 1
        
        # 确定最终等级（取众数，如果有 high 则优先关注）
        if level_counts['high'] > 0:
            final_level = 'high'
            level_label = '高风险'
        elif level_counts['medium'] > level_counts['low']:
            final_level = 'medium'
            level_label = '中等风险'
        else:
            final_level = 'low'
            level_label = '低风险'
        
        # 生成解读
        if final_level == 'low':
            interpretation = '候选人在面试过程中整体心理状态良好，未发现明显的抑郁倾向。'
        elif final_level == 'medium':
            interpretation = '候选人在面试过程中表现出一定的压力或情绪波动，建议关注其心理健康状态。'
        else:
            interpretation = '候选人在面试过程中表现出较明显的负面情绪或压力迹象，建议在录用决策时审慎考虑，或提供必要的心理支持。'
        
        return {
            'overall_score': avg_score,
            'level': final_level,
            'level_label': level_label,
            'level_distribution': level_counts,
            'interpretation': interpretation
        }
    
    async def _evaluate_dimension(
        self,
        dimension_key: str,
        candidate_profile: str,
        dimension_config: Dict
    ) -> Dict[str, Any]:
        
        dimension_name = dimension_config["name"]
        sub_dimensions = dimension_config["sub_dimensions"]
        
        system_prompt = f"""你是一位资深的人力资源评估专家，擅长基于 Rubric 量表进行候选人评估。

你需要评估候选人的【{dimension_name}】维度。

## Rubric 评分标准（1-5分）
- 5分 卓越：远超岗位要求，表现突出
- 4分 优秀：超出岗位要求，表现良好
- 3分 良好：符合岗位要求，表现合格
- 2分 一般：基本符合，但有提升空间
- 1分 不足：未达到岗位要求

## 子维度评估项
{chr(10).join([f"- {sd}" for sd in sub_dimensions])}

## 输出要求
请输出严格的 JSON 格式：
{{
    "dimension_score": <1-5的整数>,
    "sub_scores": {{
        "{sub_dimensions[0]}": <1-5>,
        "{sub_dimensions[1]}": <1-5>,
        "{sub_dimensions[2]}": <1-5>,
        "{sub_dimensions[3]}": <1-5>
    }},
    "strengths": ["优势1", "优势2"],
    "weaknesses": ["不足1", "不足2"],
    "analysis": "详细分析说明（100-200字）"
}}"""

        user_prompt = f"""请基于以下候选人资料，评估其【{dimension_name}】维度：

{candidate_profile}

请严格按照 Rubric 量表给出评分和分析。"""

        try:
            result = await self._llm.complete_json(system_prompt, user_prompt, temperature=0.3)
            result["weight"] = dimension_config["weight"]
            result["dimension_name"] = dimension_name
            return result
            
        except Exception as e:
            logger.error(f"评估维度 {dimension_name} 失败: {e}")
            return {
                "dimension_score": 3,
                "sub_scores": {sd: 3 for sd in sub_dimensions},
                "strengths": [],
                "weaknesses": [],
                "analysis": f"评估过程出现异常：{str(e)}",
                "weight": dimension_config["weight"],
                "dimension_name": dimension_name
            }
    
    def _calculate_final_score(self, dimension_scores: Dict[str, Dict]) -> float:
        """计算加权最终得分（转换为百分制）。"""
        
        total_weighted_score = 0
        total_weight = 0
        
        for dim_key, dim_data in dimension_scores.items():
            score = dim_data.get("dimension_score", 3)
            weight = dim_data.get("weight", 0.2)
            
            # 将 1-5 分转换为百分制
            normalized_score = (score - 1) / 4 * 100
            
            total_weighted_score += normalized_score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 60.0
        
        return round(total_weighted_score / total_weight, 1)
    
    def _determine_recommendation(self, final_score: float) -> Dict[str, Any]:
        """根据最终得分确定推荐等级。"""
        
        for level_key, level_config in RECOMMENDATION_LEVELS.items():
            if final_score >= level_config["min_score"]:
                return {
                    "level": level_key,
                    "label": level_config["label"],
                    "action": level_config["action"],
                    "score": final_score
                }
        
        return {
            "level": "not_recommend",
            "label": "不推荐",
            "action": "不建议录用",
            "score": final_score
        }
    
    async def _generate_comprehensive_report(
        self,
        candidate_name: str,
        candidate_profile: str,
        dimension_scores: Dict,
        psychological_analysis: Dict,
        final_score: float,
        recommendation: Dict
    ) -> str:
        """生成综合分析报告（含心理分析）。"""
        
        system_prompt = """你是一位资深的招聘决策专家，擅长撰写专业的候选人综合评估报告。

请根据各维度评估结果和心理分析数据，生成一份结构清晰、内容专业的综合分析报告。

报告要求：
1. 语言专业、客观、有建设性
2. 重点突出关键发现
3. 整合心理分析结论
4. 给出明确的录用建议
5. 控制在600字以内"""

        # 构建维度评分摘要
        dimension_summary = []
        for dim_key, dim_data in dimension_scores.items():
            dim_name = dim_data.get("dimension_name", dim_key)
            score = dim_data.get("dimension_score", 3)
            analysis = dim_data.get("analysis", "")
            dimension_summary.append(f"- {dim_name}：{score}分 - {analysis}")
        
        # 构建心理分析摘要
        big_five = psychological_analysis.get('big_five', {})
        credibility = psychological_analysis.get('credibility', {})
        depression = psychological_analysis.get('depression', {})
        
        psychological_summary = f"""
- 性格特点：{big_five.get('personality_summary', '未知')}
- 面试可信度：{credibility.get('overall_score', 0):.1%}（{credibility.get('level', '未知')}）
- 抑郁风险：{depression.get('level_label', '未知')}（平均分 {depression.get('overall_score', 0)}）
"""
        
        user_prompt = f"""请为候选人【{candidate_name}】生成综合分析报告：

## 评估结果
- 综合得分：{final_score}分
- 推荐等级：{recommendation['label']}
- 建议行动：{recommendation['action']}

## 各维度评估
{chr(10).join(dimension_summary)}

## 心理分析
{psychological_summary}

请生成一份专业的综合分析报告，包含：
1. 候选人综合评价（一句话概括）
2. 核心优势（2-3点）
3. 潜在风险（1-2点，结合心理分析）
4. 心理健康与可信度评估
5. 最终建议"""

        try:
            return await self._llm.complete(system_prompt, user_prompt, temperature=0.4)
            
        except Exception as e:
            logger.error(f"生成综合报告失败: {e}")
            return f"""## {candidate_name} 综合分析报告

**综合得分**：{final_score}分
**推荐等级**：{recommendation['label']}

### 评估说明
由于技术原因，详细报告生成失败。请参考各维度评分进行决策。

### 心理分析摘要
{psychological_summary}

### 建议
{recommendation['action']}"""
