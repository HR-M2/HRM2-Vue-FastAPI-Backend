"""
单人综合分析评估代理模块。

基于 Rubric 量表的多维度评估系统，整合：
- 简历内容
- 简历初筛报告
- 面试问答记录
- 面试分析报告
- 面试视频分析（预留）

生成最终的综合录用建议。
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
    
    def analyze(
        self,
        candidate_name: str,
        resume_content: str,
        screening_report: Dict[str, Any],
        interview_records: List[Dict[str, Any]],
        interview_report: Dict[str, Any],
        video_analysis: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        执行综合分析。
        
        参数:
            candidate_name: 候选人姓名
            resume_content: 简历内容
            screening_report: 简历初筛报告
            interview_records: 面试问答记录
            interview_report: 面试分析报告
            video_analysis: 视频分析结果（可选，预留）
            progress_callback: 进度回调函数
            
        返回:
            综合分析结果
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
            interview_records=interview_records,
            interview_report=interview_report,
            video_analysis=video_analysis
        )
        
        update_progress("专业能力评估", 20)
        
        # 2. 多维度评估
        dimension_scores = {}
        
        # 专业能力评估
        dimension_scores["professional_competency"] = self._evaluate_dimension(
            "professional_competency",
            candidate_profile,
            EVALUATION_DIMENSIONS["professional_competency"]
        )
        update_progress("工作经验评估", 35)
        
        # 工作经验评估
        dimension_scores["work_experience"] = self._evaluate_dimension(
            "work_experience",
            candidate_profile,
            EVALUATION_DIMENSIONS["work_experience"]
        )
        update_progress("软技能评估", 50)
        
        # 软技能评估
        dimension_scores["soft_skills"] = self._evaluate_dimension(
            "soft_skills",
            candidate_profile,
            EVALUATION_DIMENSIONS["soft_skills"]
        )
        update_progress("文化匹配评估", 65)
        
        # 文化匹配评估
        dimension_scores["cultural_fit"] = self._evaluate_dimension(
            "cultural_fit",
            candidate_profile,
            EVALUATION_DIMENSIONS["cultural_fit"]
        )
        update_progress("面试表现评估", 80)
        
        # 面试表现评估
        dimension_scores["interview_performance"] = self._evaluate_dimension(
            "interview_performance",
            candidate_profile,
            EVALUATION_DIMENSIONS["interview_performance"]
        )
        update_progress("生成综合报告", 90)
        
        # 3. 计算综合得分
        final_score = self._calculate_final_score(dimension_scores)
        
        # 4. 确定推荐等级
        recommendation = self._determine_recommendation(final_score)
        
        # 5. 生成综合报告
        comprehensive_report = self._generate_comprehensive_report(
            candidate_name=candidate_name,
            candidate_profile=candidate_profile,
            dimension_scores=dimension_scores,
            final_score=final_score,
            recommendation=recommendation
        )
        
        update_progress("完成", 100)
        
        return {
            "candidate_name": candidate_name,
            "final_score": final_score,
            "recommendation": recommendation,
            "dimension_scores": dimension_scores,
            "comprehensive_report": comprehensive_report,
            "rubric_scales": RUBRIC_SCALES,
            "evaluation_dimensions": EVALUATION_DIMENSIONS
        }
    
    def _build_candidate_profile(
        self,
        candidate_name: str,
        resume_content: str,
        screening_report: Dict,
        interview_records: List[Dict],
        interview_report: Dict,
        video_analysis: Optional[Dict]
    ) -> str:
        """构建候选人完整画像文本。"""
        
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
        
        # 面试问答记录（消息流格式）
        profile_parts.append("\n## 三、面试问答记录")
        if interview_records:
            for msg in interview_records:
                role = msg.get('role', '')
                content = msg.get('content', '')
                role_label = '面试官' if role == 'interviewer' else '候选人'
                profile_parts.append(f"**{role_label}**：{content}")
        else:
            profile_parts.append("无面试记录")
        
        # 面试分析报告
        profile_parts.append("\n## 四、面试分析报告")
        if interview_report:
            overall = interview_report.get('overall_assessment', {})
            profile_parts.append(f"面试评分：{overall.get('recommendation_score', 'N/A')}")
            profile_parts.append(f"面试建议：{overall.get('recommendation', 'N/A')}")
            profile_parts.append(f"总结：{overall.get('summary', '')}")
            
            if interview_report.get('highlights'):
                profile_parts.append(f"亮点：{', '.join(interview_report['highlights'])}")
            if interview_report.get('red_flags'):
                profile_parts.append(f"风险点：{', '.join(interview_report['red_flags'])}")
        else:
            profile_parts.append("无面试报告")
        
        # 视频分析（预留）
        if video_analysis:
            profile_parts.append("\n## 五、面试视频分析")
            profile_parts.append(json.dumps(video_analysis, ensure_ascii=False, indent=2))
        
        return "\n".join(profile_parts)
    
    def _evaluate_dimension(
        self,
        dimension_key: str,
        candidate_profile: str,
        dimension_config: Dict
    ) -> Dict[str, Any]:
        """评估单个维度。"""
        
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
            result = self._llm.complete_json(system_prompt, user_prompt, temperature=0.3)
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
    
    def _generate_comprehensive_report(
        self,
        candidate_name: str,
        candidate_profile: str,
        dimension_scores: Dict,
        final_score: float,
        recommendation: Dict
    ) -> str:
        """生成综合分析报告。"""
        
        system_prompt = """你是一位资深的招聘决策专家，擅长撰写专业的候选人综合评估报告。

请根据各维度评估结果，生成一份结构清晰、内容专业的综合分析报告。

报告要求：
1. 语言专业、客观、有建设性
2. 重点突出关键发现
3. 给出明确的录用建议
4. 控制在500字以内"""

        # 构建维度评分摘要
        dimension_summary = []
        for dim_key, dim_data in dimension_scores.items():
            dim_name = dim_data.get("dimension_name", dim_key)
            score = dim_data.get("dimension_score", 3)
            analysis = dim_data.get("analysis", "")
            dimension_summary.append(f"- {dim_name}：{score}分 - {analysis}")
        
        user_prompt = f"""请为候选人【{candidate_name}】生成综合分析报告：

## 评估结果
- 综合得分：{final_score}分
- 推荐等级：{recommendation['label']}
- 建议行动：{recommendation['action']}

## 各维度评估
{chr(10).join(dimension_summary)}

请生成一份专业的综合分析报告，包含：
1. 候选人综合评价（一句话概括）
2. 核心优势（2-3点）
3. 潜在风险（1-2点）
4. 最终建议"""

        try:
            return self._llm.complete(system_prompt, user_prompt, temperature=0.4)
            
        except Exception as e:
            logger.error(f"生成综合报告失败: {e}")
            return f"""## {candidate_name} 综合分析报告

**综合得分**：{final_score}分
**推荐等级**：{recommendation['label']}

### 评估说明
由于技术原因，详细报告生成失败。请参考各维度评分进行决策。

### 建议
{recommendation['action']}"""
