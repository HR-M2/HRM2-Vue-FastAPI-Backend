"""
简历筛选多代理流程。
包含评分规则生成、代理创建与管理器实现。
"""

import json
from typing import Any, Callable, Dict, List, Optional, Tuple

import autogen
from autogen import AssistantAgent, UserProxyAgent, GroupChat

from .llm_client import get_llm_client
from .base import BaseAgentManager

# ---------------------- 提示词模板 ----------------------
USER_PROXY_SYSTEM_PROMPT = """
你代表企业招聘负责人。你的职责是：
1. 提供招聘标准文件路径和简历内容
2. 协调三个评审专家的评分工作
3. 汇总最终评分结果并做出招聘建议
回复 TERMINATE 表示评审完成。
""".strip()

ASSISTANT_SYSTEM_PROMPT = """
你是招聘系统协调员。你的职责是：
1. 读取并解析招聘标准文件
2. 生成量化评分表格
3. 将简历内容分发给三个评审专家，只需要向他们提出要求，但是你不需要说出他们的意见
请确保评分过程公正、标准统一。
""".strip()

HR_SYSTEM_PROMPT = """
你是企业HR专家，专注于人才的综合素质评估。请根据以下标准进行评分：
{hr_rules}

评分要点：
1. 工作经验匹配度（年限、行业相关性）
2. 学历背景和证书资质
3. 职业稳定性和发展潜力
4. 沟通表达能力和文化契合度

请对简历进行详细分析，给出0-100分的评分，并提供具体的评分理由。
在你自己评分的基础上，单独列出一行，在本岗位参考月薪资范围内给出你认为合适的薪资。
你只需要从你HR的角度提出意见和理由。
评分格式（显示评分的部分不要加任何格式）：HR评分：[分数]分，理由：[详细分析]，建议月薪：[建议薪资]
""".strip()

TECH_SYSTEM_PROMPT = """
你是技术评审专家，专注于技术能力评估。请根据以下标准进行评分：
{tech_rules}

评分要点：
1. 技术技能栈的完整度和深度
2. 项目经验的技术复杂度和相关性
3. 技术成长潜力和学习能力
4. 问题解决能力和创新思维

请对简历进行详细技术分析，给出0-100分的评分，并提供具体的技术评价。
在你自己评分的基础上，单独列出一行，在本岗位参考月薪资范围内给出你认为合适的薪资。
你只需要从你技术骨干的角度提出意见和理由。
评分格式（显示评分的部分不要加任何格式）：技术评分：[分数]分，理由：[技术分析]，建议月薪：[建议薪资]
""".strip()

PM_SYSTEM_PROMPT = """
你是项目经理专家，专注于项目管理能力评估。请根据以下标准进行评分：
{pm_rules}

评分要点：
1. 项目管理经验和成果
2. 团队协作和沟通能力
3. 领导力和决策能力
4. 项目执行力和风险管理能力

请从项目管理角度分析简历，给出0-100分的评分，并提供具体的管理能力评价。
在你自己评分的基础上，单独列出一行，在本岗位参考月薪资范围内给出你认为合适的薪资。
你只需要从你项目经理的角度提出意见和理由。
评分格式（显示评分的部分不要加任何格式）：管理评分：[分数]分，理由：[管理能力分析]，建议月薪：[建议薪资]
""".strip()

CRITIC_SYSTEM_PROMPT = """
你是综合评审专家。你的职责是：
1. 汇总三个专家的评分结果
2. 计算最终综合评分（满分100分）
3. 提供综合招聘建议
4. 指出候选人的优势和不足
5. 结合各专家给出的薪资建议，提出最终的建议月薪

请确保评分计算准确，建议合理。最终回复应包含：
- 各维度得分和综合得分
- 候选人优势分析
- 改进建议和面试重点
- 最终的招聘建议（推荐面试/备选/不匹配）
- 最终的建议月薪（如果最终的招聘建议是"不匹配"，则不需要提供月薪建议）

请在你的发言开头给出综合评分，
评分格式（显示评分的部分不要加任何格式）：综合评分：[分数]分

量化评分标准如下：
职位：{position}
必备技能：{required_skills}
最低经验：{min_experience}年
参考月薪资：{salary_range}
回复 APPROVE 表示评审完成。
""".strip()

GROUP_MANAGER_PROMPT = """
你是一个高效的会议主持人，负责协调简历评审会议。

当前量化评分标准如下：
职位：{position}
必备技能：{required_skills}
最低经验：{min_experience}年
参考月薪资：{salary_range}
""".strip()

RUN_SCREENING_MESSAGE = """
我们需要对一份求职简历进行综合评审。

招聘标准概述：
- 职位：{position}
- 必备技能：{required_skills}
- 最低经验：{min_experience}年
- 参考月薪资：{salary_range}

姓名：{candidate_name}

简历内容：
{resume_text}

请开始评审流程。
""".strip()


# ---------------------- 评分规则 ----------------------
def generate_scoring_rules(criteria: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """根据招聘条件生成评分规则。"""
    return {
        "hr_dimension": [
            {"item": "工作经验", "max_score": 30, "rule": f"≥{criteria.get('min_experience', 2)}年经验"},
            {"item": "学历背景", "max_score": 25, "rule": f"学历要求: {', '.join(criteria.get('education', []))}"},
            {"item": "证书资质", "max_score": 20, "rule": "相关专业证书"},
            {"item": "职业稳定性", "max_score": 25, "rule": "工作经历连续性"},
        ],
        "technical_dimension": [
            {"item": "必备技能", "max_score": 40, "rule": f"掌握: {', '.join(criteria.get('required_skills', []))}"},
            {"item": "附加技能", "max_score": 30, "rule": f"加分项: {', '.join(criteria.get('optional_skills', []))}"},
            {"item": "技术深度", "max_score": 30, "rule": "项目经验和技术理解深度"},
        ],
        "manager_dimension": [
            {
                "item": "项目管理",
                "max_score": 35,
                "rule": f"至少{criteria.get('project_requirements', {}).get('min_projects', 2)}个完整项目",
            },
            {"item": "团队协作", "max_score": 30, "rule": "团队合作和沟通能力"},
            {
                "item": "领导能力",
                "max_score": 35,
                "rule": "团队领导经验" if criteria.get("project_requirements", {}).get("team_lead_experience", True) else "项目参与经验",
            },
        ],
    }


# ---------------------- 代理创建 ----------------------
def create_screening_agents(criteria: Dict[str, Any]) -> Tuple[UserProxyAgent, AssistantAgent, AssistantAgent, AssistantAgent, AssistantAgent, AssistantAgent]:
    """根据招聘条件创建筛选代理。"""
    llm_config = get_llm_client().get_autogen_config()
    scoring_rules = generate_scoring_rules(criteria)

    def _fmt_rules(rules: List[Dict[str, Any]]) -> str:
        """格式化规则为可读字符串。"""
        return json.dumps(rules, ensure_ascii=False, indent=2)

    user_proxy = UserProxyAgent(
        name="User_Proxy",
        human_input_mode="TERMINATE",
        max_consecutive_auto_reply=10,
        code_execution_config=False,
        system_message=USER_PROXY_SYSTEM_PROMPT,
    )

    assistant = AssistantAgent(
        name="Assistant",
        llm_config=llm_config,
        system_message=ASSISTANT_SYSTEM_PROMPT,
    )

    hr_agent = AssistantAgent(
        name="HR_Expert",
        llm_config=llm_config,
        system_message=HR_SYSTEM_PROMPT.format(hr_rules=_fmt_rules(scoring_rules["hr_dimension"])),
    )

    technical_agent = AssistantAgent(
        name="Technical_Expert",
        llm_config=llm_config,
        system_message=TECH_SYSTEM_PROMPT.format(tech_rules=_fmt_rules(scoring_rules["technical_dimension"])),
    )

    manager_agent = AssistantAgent(
        name="Project_Manager_Expert",
        llm_config=llm_config,
        system_message=PM_SYSTEM_PROMPT.format(pm_rules=_fmt_rules(scoring_rules["manager_dimension"])),
    )

    position = criteria.get("position", "未知职位")
    required_skills = ", ".join(criteria.get("required_skills", []))
    min_experience = criteria.get("min_experience", 2)
    salary_range = criteria.get("salary_range", [8000, 20000])
    salary_range_str = f"{salary_range[0]}~{salary_range[1]}元"

    critic = AssistantAgent(
        name="Critic",
        llm_config=llm_config,
        system_message=CRITIC_SYSTEM_PROMPT.format(
            position=position,
            required_skills=required_skills,
            min_experience=min_experience,
            salary_range=salary_range_str,
        ),
    )

    return user_proxy, assistant, hr_agent, technical_agent, manager_agent, critic


# ---------------------- 管理器实现 ----------------------
class ScreeningAgentManager(BaseAgentManager):
    """简历筛选代理管理器。"""

    def __init__(self, criteria: Dict[str, Any]):
        super().__init__(criteria)
        self.weights = {"hr": 0.3, "technical": 0.4, "manager": 0.3}

    def setup(self):
        """创建代理与群聊。"""
        agents = create_screening_agents(self.criteria)
        (
            self.user_proxy,
            self.assistant,
            self.hr_agent,
            self.technical_agent,
            self.manager_agent,
            self.critic,
        ) = agents

        def speaker_selector(last_speaker: Optional[autogen.Agent], groupchat: GroupChat):
            """轮询发言人，并更新进度。"""
            speaker_sequence = {
                "User_Proxy": "Assistant",
                "Assistant": "HR_Expert",
                "HR_Expert": "Technical_Expert",
                "Technical_Expert": "Project_Manager_Expert",
                "Project_Manager_Expert": "Critic",
                "Critic": None,
            }

            if last_speaker is None:
                next_speaker = groupchat.agent_by_name("User_Proxy")
            else:
                next_speaker_name = speaker_sequence.get(last_speaker.name)
                next_speaker = groupchat.agent_by_name(next_speaker_name) if next_speaker_name else None

            if next_speaker:
                self.speakers.append(next_speaker.name)
                self.update_task_speaker(next_speaker.name, len(self.speakers))

            return next_speaker

        self.create_group_chat(
            agents=list(agents),
            speaker_selector=speaker_selector,
            max_round=12,
        )

        position = self.criteria.get("position", "未知职位")
        required_skills = ", ".join(self.criteria.get("required_skills", []))
        min_experience = self.criteria.get("min_experience", 2)
        salary_range = self.criteria.get("salary_range", [8000, 20000])
        salary_range_str = f"{salary_range[0]}~{salary_range[1]}元"

        system_message = GROUP_MANAGER_PROMPT.format(
            position=position,
            required_skills=required_skills,
            min_experience=min_experience,
            salary_range=salary_range_str,
        )
        self.create_manager(system_message=system_message)

    def run_screening(self, candidate_name: str, resume_text: str) -> List[Dict[str, Any]]:
        """运行筛选流程，返回对话消息列表。"""
        position = self.criteria.get("position", "未知职位")
        required_skills = ", ".join(self.criteria.get("required_skills", []))
        min_experience = self.criteria.get("min_experience", 2)
        salary_range = self.criteria.get("salary_range", [8000, 20000])
        salary_range_str = f"{salary_range[0]}~{salary_range[1]}元"

        message = RUN_SCREENING_MESSAGE.format(
            position=position,
            required_skills=required_skills,
            min_experience=min_experience,
            salary_range=salary_range_str,
            candidate_name=candidate_name,
            resume_text=resume_text,
        )

        return self.run_chat(self.user_proxy, message)
