"""
开发测试工具：随机简历生成。
"""

import hashlib
import random
from typing import Dict, Any, List
from loguru import logger

from .llm_client import get_llm_client

# ================= 提示词模板 =================

SYSTEM_PROMPT_GENERATE_RESUME = """你是一个简历生成器，用于生成测试数据。请根据给定的岗位要求生成一份虚构但真实感强的简历。

要求：
1. 简历内容要有一定的随机性和多样性
2. 候选人的背景、技能水平、工作经验应该有变化（不要每次都是完美匹配）
3. 有些简历可以是优秀候选人，有些可以是一般候选人，有些可以是不太匹配的候选人
4. 简历格式要自然，像真实简历一样
5. 包含：基本信息、教育背景、工作经历、项目经验、技能特长、自我评价等
6. 工作经历和项目经验要具体，包含时间、公司/项目名称、职责描述
7. 技能水平可以随机（精通/熟练/了解）
8. 教育背景可以随机（本科/硕士/大专等）

直接输出简历内容文本，不要有任何额外说明。"""

USER_PROMPT_TEMPLATE = """请为候选人“{candidate_name}”生成一份应聘以下岗位的简历：

岗位名称：{position}
岗位描述：{description}
必备技能：{required_skills}
可选技能：{optional_skills}
最低经验：{min_experience}年
学历要求：{education}

请生成一份完整的简历，确保内容有一定随机性。这次生成的候选人匹配程度请随机决定（可能是很匹配、一般匹配或不太匹配）。"""


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

        user_prompt = USER_PROMPT_TEMPLATE.format(
            candidate_name=candidate_name,
            position=position_data.get("title", "未知岗位"),
            description=position_data.get("description", ""),
            required_skills=", ".join(position_data.get("required_skills", [])),
            optional_skills=", ".join(position_data.get("optional_skills", [])),
            min_experience=position_data.get("min_experience", 0),
            education=", ".join(position_data.get("education", [])),
        )

        content = await self._llm.complete(
            SYSTEM_PROMPT_GENERATE_RESUME,
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
