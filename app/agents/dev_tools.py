# -*- coding: utf-8 -*-
"""
开发测试工具：随机简历生成。
"""

import hashlib
import random
from typing import Dict, Any, List
from loguru import logger

from .llm_client import get_llm_client
from .prompts import get_prompt


# ================= 随机姓名字符集 =================

SURNAMES = [
    "张", "王", "李", "赵", "刘", "陈", "杨", "黄", "周", "吴",
    "徐", "孙", "马", "朱", "胡", "郭", "何", "林", "罗", "高",
    "郑", "梁", "谢", "宋", "唐", "韩", "冯", "邓", "曹", "许",
]

GIVEN_NAMES = [
    "伟", "芳", "娜", "敏", "静", "丽", "强", "磊", "军", "洋",
    "勇", "艳", "杰", "涛", "明", "超", "秀", "华", "慧", "巧",
    "美", "娟", "英", "玲", "桂", "萍", "红", "玉", "霞", "晶",
    "辉", "峰", "浩", "宇", "鑫", "龙", "凯", "博", "翔", "鹏",
    "思", "雨", "欣", "琳", "怡", "婷", "洁", "雪", "晨", "阳",
]


def _generate_random_name() -> str:
    """生成随机中文姓名。"""
    surname = random.choice(SURNAMES)
    given = random.choice(GIVEN_NAMES)
    if random.random() > 0.4:
        given += random.choice(GIVEN_NAMES)
    return surname + given


class DevToolsService:
    """开发测试工具服务。"""

    def __init__(self):
        self._llm = get_llm_client()

    async def generate_random_resume(self, position_data: Dict[str, Any], candidate_name: str | None = None) -> Dict[str, str]:
        """生成单份随机简历。"""
        candidate_name = candidate_name or _generate_random_name()

        user_prompt = get_prompt(
            "dev_tools", "generate_resume_user",
            candidate_name=candidate_name,
            position=position_data.get("title", "未知岗位"),
            description=position_data.get("description", ""),
            required_skills=", ".join(position_data.get("required_skills", [])),
            optional_skills=", ".join(position_data.get("optional_skills", [])),
            min_experience=position_data.get("min_experience", 0),
            education=", ".join(position_data.get("education", [])),
        )

        system_prompt = get_prompt("dev_tools", "generate_resume_system")
        content = await self._llm.complete(
            system_prompt,
            user_prompt,
            temperature=0.9,
        )

        hash_input = f"{candidate_name}_{content}_{random.random()}"
        file_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        return {
            "name": f"{candidate_name}_简历.txt",
            "content": content,
            "file_hash": file_hash,
            "candidate_name": candidate_name,
        }

    async def generate_batch_resumes(self, position_data: Dict[str, Any], count: int = 5) -> List[Dict[str, str]]:
        """批量生成随机简历。"""
        count = max(1, min(20, count))
        resumes: List[Dict[str, str]] = []
        used_names = set()

        for _ in range(count):
            name = _generate_random_name()
            while name in used_names:
                name = _generate_random_name()
            used_names.add(name)
            try:
                resume = await self.generate_random_resume(position_data, name)
                resumes.append(resume)
            except Exception as exc:
                logger.error("生成简历失败: {}", exc)
                continue

        return resumes


_dev_tools_service: DevToolsService | None = None


def get_dev_tools_service() -> DevToolsService:
    """获取 DevToolsService 单例。"""
    global _dev_tools_service
    if _dev_tools_service is None:
        _dev_tools_service = DevToolsService()
    return _dev_tools_service
