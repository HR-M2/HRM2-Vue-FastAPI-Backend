"""
AI Agents 模块

提供 HR 智能招聘系统的 AI 代理服务：
- PositionService: 智能岗位需求生成
- ScreeningAgentManager: 多代理简历筛选
- InterviewService: 智能面试辅助
- AnalysisService: 综合评估分析
- ExperienceManager: 经验学习与检索
- DevToolsService: 开发测试工具
"""

from .llm_client import get_llm_client, get_embedding_config, get_task_limiter
from .dev_tools import get_dev_tools_service, DevToolsService
from .analysis import AnalysisService, get_analysis_service
from .interview import InterviewService, get_interview_service
from .position import PositionService, get_position_service
from .screening import ScreeningAgentManager, create_screening_agents
from .experience_manager import ExperienceManager, get_experience_manager

__all__ = [
    "get_llm_client",
    "get_embedding_config",
    "get_task_limiter",
    "DevToolsService",
    "get_dev_tools_service",
    "AnalysisService",
    "get_analysis_service",
    "InterviewService",
    "get_interview_service",
    "PositionService",
    "get_position_service",
    "ScreeningAgentManager",
    "create_screening_agents",
    "ExperienceManager",
    "get_experience_manager",
]

