"""
基础代理管理工具模块。
"""
import autogen
from autogen import GroupChat, GroupChatManager
from typing import List, Dict, Any, Callable, Optional
from .llm_config import get_llm_config


class BaseAgentManager:
    """管理autogen代理的基类。"""
    
    def __init__(self, criteria: Dict[str, Any] = None):
        self.llm_config = get_llm_config()
        self.criteria = criteria or {}
        self.agents = []
        self.group_chat = None
        self.manager = None
        self.current_task = None
        self.messages = []
        self.speakers = []
    
    def set_task(self, task):
        """设置当前任务以便进度跟踪。"""
        self.current_task = task
    
    def create_group_chat(
        self,
        agents: List[autogen.Agent],
        speaker_selector: Callable,
        max_round: int = 12
    ) -> GroupChat:
        """使用给定的代理创建群聊。"""
        self.agents = agents
        self.group_chat = GroupChat(
            agents=agents,
            messages=[],
            max_round=max_round,
            speaker_selection_method=speaker_selector,
        )
        return self.group_chat
    
    def create_manager(
        self,
        system_message: str = "",
        termination_checker: Callable = None
    ) -> GroupChatManager:
        """创建群聊管理器。"""
        if not self.group_chat:
            raise ValueError("Group chat must be created first")
        
        self.manager = GroupChatManager(
            groupchat=self.group_chat,
            llm_config=self.llm_config,
            is_termination_msg=termination_checker or self.default_termination_checker,
            system_message=system_message
        )
        return self.manager
    
    @staticmethod
    def default_termination_checker(content: Any) -> bool:
        """默认终止条件检查器。"""
        if not content:
            return False
        content_str = str(content).lower()
        return any(keyword in content_str for keyword in ['approve', 'terminate', '评审结束'])
    
    # 筛选流程中的agent总数（用于进度计算）
    TOTAL_AGENTS = 6  # User_Proxy -> Assistant -> HR_Expert -> Technical_Expert -> Project_Manager_Expert -> Critic
    
    def update_task_speaker(self, speaker_name: str, step: int = None):
        """
        更新任务的当前发言人信息。
        
        参数:
            speaker_name: 当前发言的agent名称
            step: 当前步骤数（1-6），会自动转换为百分比进度
        """
        if self.current_task:
            self.current_task.current_speaker = speaker_name
            if step is not None:
                # 按agent总数计算百分比进度（0-100）
                progress_percent = int((step / self.TOTAL_AGENTS) * 100)
                self.current_task.progress = min(progress_percent, 99)  # 保留最后1%给完成状态
            # 注意：FastAPI中可能需要不同的持久化方式，这里保留接口
    
    def run_chat(self, initiator: autogen.Agent, message: str):
        """运行代理聊天。"""
        if not self.manager:
            raise ValueError("Manager must be created first")
        
        initiator.initiate_chat(self.manager, message=message)
        self.messages = self.group_chat.messages if self.group_chat else []
        return self.messages
