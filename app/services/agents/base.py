"""
autogen 群聊基类封装。
"""
import autogen
from autogen import GroupChat, GroupChatManager
from typing import List, Dict, Any, Callable, Optional

from .llm_client import get_llm_client
from app.core.progress_cache import progress_cache


class BaseAgentManager:
    """管理 autogen 代理的基类。"""

    def __init__(self, criteria: Optional[Dict[str, Any]] = None):
        self.llm_config = get_llm_client().get_autogen_config()
        self.criteria = criteria or {}
        self.agents = []
        self.group_chat = None
        self.manager = None
        self.task_id: Optional[str] = None
        self.messages: List[Dict[str, Any]] = []
        self.speakers: List[str] = []

    def set_task_id(self, task_id: str):
        """设置任务 ID，用于进度跟踪。"""
        self.task_id = task_id

    def create_group_chat(
        self,
        agents: List[autogen.Agent],
        speaker_selector: Callable,
        max_round: int = 12,
    ) -> "GroupChat":
        """创建群聊。"""
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
        termination_checker: Optional[Callable] = None,
    ) -> "GroupChatManager":
        """创建群聊管理器。"""
        if not self.group_chat:
            raise ValueError("群聊未创建")

        self.manager = GroupChatManager(
            groupchat=self.group_chat,
            llm_config=self.llm_config,
            is_termination_msg=termination_checker or self.default_termination_checker,
            system_message=system_message,
        )
        return self.manager

    @staticmethod
    def default_termination_checker(content: Any) -> bool:
        """默认终止条件。"""
        if not content:
            return False
        content_str = str(content).lower()
        return any(keyword in content_str for keyword in ["approve", "terminate", "评审结束"])

    TOTAL_AGENTS = 6  # User_Proxy -> Assistant -> HR_Expert -> Technical_Expert -> Project_Manager_Expert -> Critic

    def update_task_speaker(self, speaker_name: str, step: Optional[int] = None):
        """写入当前发言人到进度缓存。"""
        if self.task_id:
            progress_cache.update(task_id=self.task_id, current_speaker=speaker_name, step=step)

    def run_chat(self, initiator: autogen.Agent, message: str):
        """运行群聊。"""
        if not self.manager:
            raise ValueError("Manager must be created first")
        initiator.initiate_chat(self.manager, message=message)
        self.messages = self.group_chat.messages if self.group_chat else []
        return self.messages
