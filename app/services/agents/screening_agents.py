"""
简历评估的筛选代理模块。
"""
import autogen
from autogen import AssistantAgent, UserProxyAgent, GroupChat
from typing import Dict, Any, List, Tuple, Callable
from .llm_config import get_llm_config
from .base import BaseAgentManager


def create_screening_agents(criteria: Dict[str, Any]) -> Tuple:
    """
    根据招聘条件创建简历筛选代理。
    
    参数:
        criteria: 包含职位信息的招聘条件字典
        
    返回:
        元组 (user_proxy, assistant, hr_agent, technical_agent, manager_agent, critic)
    """
    llm_config = get_llm_config()
    
    # 根据招聘条件生成评分规则
    scoring_rules = generate_scoring_rules(criteria)
    
    # 1. 用户代理
    user_proxy = UserProxyAgent(
        name="User_Proxy",
        human_input_mode="TERMINATE",
        max_consecutive_auto_reply=10,
        code_execution_config=False,
        system_message="""你代表企业招聘负责人。你的职责是：
        1. 提供招聘标准文件路径和简历内容
        2. 协调三个评审专家的评分工作
        3. 汇总最终评分结果并做出招聘建议
        回复 TERMINATE 表示评审完成。"""
    )
    
    # 2. 助手代理
    assistant = AssistantAgent(
        name="Assistant",
        llm_config=llm_config,
        system_message="""你是招聘系统协调员。你的职责是：
        1. 读取并解析招聘标准文件
        2. 生成量化评分表格
        3. 将简历内容分发给三个评审专家，只需要向他们提出要求，但是你不需要说出他们的意见
        请确保评分过程公正、标准统一。"""
    )
    
    # 3. HR专家代理
    hr_agent = AssistantAgent(
        name="HR_Expert",
        llm_config=llm_config,
        system_message=f"""你是企业HR专家，专注于人才的综合素质评估。请根据以下标准进行评分：
        {scoring_rules['hr_dimension']}

        评分要点：
        1. 工作经验匹配度（年限、行业相关性）
        2. 学历背景和证书资质
        3. 职业稳定性和发展潜力
        4. 沟通表达能力和文化契合度

        请对简历进行详细分析，给出0-100分的评分，并提供具体的评分理由。
        在你自己评分的基础上，单独列出一行，在本岗位参考月薪资范围内给出你认为合适的薪资。
        你只需要从你HR的角度提出意见和理由。
        评分格式（显示评分的部分不要加任何格式）：HR评分：[分数]分，理由：[详细分析]，建议月薪：[建议薪资]"""
    )
    
    # 4. 技术专家代理
    technical_agent = AssistantAgent(
        name="Technical_Expert",
        llm_config=llm_config,
        system_message=f"""你是技术评审专家，专注于技术能力评估。请根据以下标准进行评分：
        {scoring_rules['technical_dimension']}

        评分要点：
        1. 技术技能栈的完整度和深度
        2. 项目经验的技术复杂度和相关性
        3. 技术成长潜力和学习能力
        4. 问题解决能力和创新思维

        请对简历进行详细技术分析，给出0-100分的评分，并提供具体的技术评价。
        在你自己评分的基础上，单独列出一行，在本岗位参考月薪资范围内给出你认为合适的薪资。
        你只需要从你技术骨干的角度提出意见和理由。
        评分格式（显示评分的部分不要加任何格式）：技术评分：[分数]分，理由：[技术分析]，建议月薪：[建议薪资]"""
    )
    
    # 5. 项目经理专家代理
    manager_agent = AssistantAgent(
        name="Project_Manager_Expert",
        llm_config=llm_config,
        system_message=f"""你是项目经理专家，专注于项目管理能力评估。请根据以下标准进行评分：
        {scoring_rules['manager_dimension']}

        评分要点：
        1. 项目管理经验和成果
        2. 团队协作和沟通能力
        3. 领导力和决策能力
        4. 项目执行力和风险管理能力

        请从项目管理角度分析简历，给出0-100分的评分，并提供具体的管理能力评价。
        在你自己评分的基础上，单独列出一行，在本岗位参考月薪资范围内给出你认为合适的薪资。
        你只需要从你项目经理的角度提出意见和理由。
        评分格式（显示评分的部分不要加任何格式）：管理评分：[分数]分，理由：[管理能力分析]，建议月薪：[建议薪资]"""
    )
    
    # 6. 评审专家代理
    position = criteria.get('position', '未知职位')
    required_skills = ', '.join(criteria.get('required_skills', []))
    min_experience = criteria.get('min_experience', 2)
    salary_range = criteria.get('salary_range', [8000, 20000])
    
    critic = AssistantAgent(
        name="Critic",
        llm_config=llm_config,
        system_message=f"""你是综合评审专家。你的职责是：
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
        参考月薪资：{salary_range[0]}~{salary_range[1]}元
        回复 APPROVE 表示评审完成。"""
    )
    
    return user_proxy, assistant, hr_agent, technical_agent, manager_agent, critic


def generate_scoring_rules(criteria: Dict[str, Any]) -> Dict[str, List]:
    """根据招聘条件生成详细的评分规则。"""
    return {
        "hr_dimension": [
            {"item": "工作经验", "max_score": 30, "rule": f"≥{criteria.get('min_experience', 2)}年经验"},
            {"item": "学历背景", "max_score": 25, "rule": f"学历要求: {', '.join(criteria.get('education', []))}"},
            {"item": "证书资质", "max_score": 20, "rule": "相关专业证书"},
            {"item": "职业稳定性", "max_score": 25, "rule": "工作经历连续性"}
        ],
        "technical_dimension": [
            {"item": "必备技能", "max_score": 40, "rule": f"掌握: {', '.join(criteria.get('required_skills', []))}"},
            {"item": "附加技能", "max_score": 30, "rule": f"加分项: {', '.join(criteria.get('optional_skills', []))}"},
            {"item": "技术深度", "max_score": 30, "rule": "项目经验和技术理解深度"}
        ],
        "manager_dimension": [
            {"item": "项目管理", "max_score": 35, "rule": f"至少{criteria.get('project_requirements', {}).get('min_projects', 2)}个完整项目"},
            {"item": "团队协作", "max_score": 30, "rule": "团队合作和沟通能力"},
            {"item": "领导能力", "max_score": 35, "rule": "团队领导经验" if criteria.get('project_requirements', {}).get('team_lead_experience', True) else "项目参与经验"}
        ]
    }


class ScreeningAgentManager(BaseAgentManager):
    """简历筛选代理管理器。"""
    
    def __init__(self, criteria: Dict[str, Any]):
        super().__init__(criteria)
        self.weights = {"hr": 0.3, "technical": 0.4, "manager": 0.3}
    
    def setup(self):
        """设置所有筛选代理和群聊。"""
        agents = create_screening_agents(self.criteria)
        self.user_proxy, self.assistant, self.hr_agent, self.technical_agent, self.manager_agent, self.critic = agents
        
        # 创建发言人选择器
        def speaker_selector(last_speaker: autogen.Agent, groupchat: GroupChat):
            speaker_sequence = {
                "User_Proxy": "Assistant",
                "Assistant": "HR_Expert",
                "HR_Expert": "Technical_Expert",
                "Technical_Expert": "Project_Manager_Expert",
                "Project_Manager_Expert": "Critic",
                "Critic": None
            }
            
            if last_speaker is None:
                next_speaker = groupchat.agent_by_name("User_Proxy")
            else:
                next_speaker_name = speaker_sequence.get(last_speaker.name)
                if next_speaker_name:
                    next_speaker = groupchat.agent_by_name(next_speaker_name)
                else:
                    next_speaker = None
            
            # 更新任务进度
            if next_speaker:
                self.speakers.append(next_speaker.name)
                self.update_task_speaker(next_speaker.name, len(self.speakers))
            
            return next_speaker
        
        # 创建群聊
        self.create_group_chat(
            agents=list(agents),
            speaker_selector=speaker_selector,
            max_round=12
        )
        
        # 创建管理器
        position = self.criteria.get('position', '未知职位')
        required_skills = ', '.join(self.criteria.get('required_skills', []))
        min_experience = self.criteria.get('min_experience', 2)
        salary_range = self.criteria.get('salary_range', [8000, 20000])
        
        system_message = f"""你是一个高效的会议主持人，负责协调简历评审会议。
        
        当前量化评分标准如下：
        职位：{position}
        必备技能：{required_skills}
        最低经验：{min_experience}年
        参考月薪资：{salary_range[0]}~{salary_range[1]}元"""
        
        self.create_manager(system_message=system_message)
    
    def run_screening(self, candidate_name: str, resume_text: str) -> List[Dict]:
        """为候选人运行筛选流程。"""
        position = self.criteria.get('position', '未知职位')
        required_skills = ', '.join(self.criteria.get('required_skills', []))
        min_experience = self.criteria.get('min_experience', 2)
        salary_range = self.criteria.get('salary_range', [8000, 20000])
        
        message = f"""我们需要对一份求职简历进行综合评审。

招聘标准概述：
- 职位：{position}
- 必备技能：{required_skills}
- 最低经验：{min_experience}年
- 参考月薪资：{salary_range[0]}~{salary_range[1]}元

姓名：{candidate_name}

简历内容：
{resume_text}

请开始评审流程。"""
        
        return self.run_chat(self.user_proxy, message)
