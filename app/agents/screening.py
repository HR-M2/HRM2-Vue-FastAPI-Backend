# -*- coding: utf-8 -*-
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
from .prompts import get_prompt


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
        system_message=get_prompt("screening", "user_proxy_system"),
    )

    assistant = AssistantAgent(
        name="Assistant",
        llm_config=llm_config,
        system_message=get_prompt("screening", "assistant_system"),
    )

    hr_agent = AssistantAgent(
        name="HR_Expert",
        llm_config=llm_config,
        system_message=get_prompt("screening", "hr_system", hr_rules=_fmt_rules(scoring_rules["hr_dimension"])),
    )

    technical_agent = AssistantAgent(
        name="Technical_Expert",
        llm_config=llm_config,
        system_message=get_prompt("screening", "tech_system", tech_rules=_fmt_rules(scoring_rules["technical_dimension"])),
    )

    manager_agent = AssistantAgent(
        name="Project_Manager_Expert",
        llm_config=llm_config,
        system_message=get_prompt("screening", "pm_system", pm_rules=_fmt_rules(scoring_rules["manager_dimension"])),
    )

    position = criteria.get("position", criteria.get("title", "未知职位"))
    required_skills = ", ".join(criteria.get("required_skills", []))
    min_experience = criteria.get("min_experience", 2)
    salary_range = criteria.get("salary_range", [8000, 20000])
    salary_range_str = f"{salary_range[0]}~{salary_range[1]}元"

    critic = AssistantAgent(
        name="Critic",
        llm_config=llm_config,
        system_message=get_prompt(
            "screening", "critic_system",
            position=position,
            required_skills=required_skills,
            min_experience=min_experience,
            salary_range=salary_range_str,
        ) + ("\n\n" + criteria.get("experience_guidance", "") if criteria.get("experience_guidance") else ""),
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

        position = self.criteria.get("position", self.criteria.get("title", "未知职位"))
        required_skills = ", ".join(self.criteria.get("required_skills", []))
        min_experience = self.criteria.get("min_experience", 2)
        salary_range = self.criteria.get("salary_range", [8000, 20000])
        salary_range_str = f"{salary_range[0]}~{salary_range[1]}元"

        system_message = get_prompt(
            "screening", "group_manager",
            position=position,
            required_skills=required_skills,
            min_experience=min_experience,
            salary_range=salary_range_str,
        )
        self.create_manager(system_message=system_message)

    def run_screening(self, candidate_name: str, resume_text: str) -> List[Dict[str, Any]]:
        """运行筛选流程，返回对话消息列表。"""
        position = self.criteria.get("position", self.criteria.get("title", "未知职位"))
        required_skills = ", ".join(self.criteria.get("required_skills", []))
        min_experience = self.criteria.get("min_experience", 2)
        salary_range = self.criteria.get("salary_range", [8000, 20000])
        salary_range_str = f"{salary_range[0]}~{salary_range[1]}元"

        message = get_prompt(
            "screening", "run_screening_message",
            position=position,
            required_skills=required_skills,
            min_experience=min_experience,
            salary_range=salary_range_str,
            candidate_name=candidate_name,
            resume_text=resume_text,
        )

        return self.run_chat(self.user_proxy, message)
