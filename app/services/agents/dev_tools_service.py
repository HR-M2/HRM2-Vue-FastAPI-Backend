"""
开发测试工具服务模块。
提供开发辅助功能，如生成随机简历等。
"""
import json
import random
import hashlib
import logging
from typing import Dict, Any, List

from .llm_client import get_llm_client

logger = logging.getLogger(__name__)

# 随机姓名生成用的字符
SURNAMES = ['张', '王', '李', '赵', '刘', '陈', '杨', '黄', '周', '吴', 
            '徐', '孙', '马', '朱', '胡', '郭', '何', '林', '罗', '高',
            '郑', '梁', '谢', '宋', '唐', '韩', '冯', '邓', '曹', '许']

GIVEN_NAMES = ['伟', '芳', '娜', '敏', '静', '丽', '强', '磊', '军', '洋',
               '勇', '艳', '杰', '涛', '明', '超', '秀', '华', '慧', '巧',
               '美', '娟', '英', '玲', '桂', '萍', '红', '玉', '霞', '晶',
               '辉', '峰', '浩', '宇', '鑫', '龙', '凯', '博', '翔', '鹏',
               '思', '雨', '欣', '琳', '怡', '婷', '洁', '雪', '晨', '阳']


def generate_random_name() -> str:
    """生成随机中文姓名"""
    surname = random.choice(SURNAMES)
    # 名字1-2个字
    if random.random() > 0.4:
        given_name = random.choice(GIVEN_NAMES) + random.choice(GIVEN_NAMES)
    else:
        given_name = random.choice(GIVEN_NAMES)
    return surname + given_name


class DevToolsService:
    """开发测试工具服务"""
    
    def __init__(self):
        self._llm = get_llm_client()
    
    async def generate_random_resume(self, position_data: Dict[str, Any], candidate_name: str = None) -> Dict[str, str]:
        if not candidate_name:
            candidate_name = generate_random_name()
        
        # 构建prompt
        system_prompt = """你是一个简历生成器，用于生成测试数据。请根据给定的岗位要求生成一份虚构但真实感强的简历。

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

        position_info = f"""
岗位名称：{position_data.get('position', '未知岗位')}
岗位描述：{position_data.get('description', '')}
必备技能：{', '.join(position_data.get('required_skills', []))}
可选技能：{', '.join(position_data.get('optional_skills', []))}
最低经验：{position_data.get('min_experience', 0)}年
学历要求：{', '.join(position_data.get('education', []))}
"""

        user_message = f"""请为候选人"{candidate_name}"生成一份应聘以下岗位的简历：

{position_info}

请生成一份完整的简历，确保内容有一定随机性。这次生成的候选人匹配程度请随机决定（可能是很匹配、一般匹配或不太匹配）。"""

        try:
            content = await self._llm.complete(system_prompt, user_message, temperature=0.9)
            
            hash_input = f"{candidate_name}_{content}_{random.random()}"
            file_hash = hashlib.sha256(hash_input.encode()).hexdigest()
            
            return {
                'name': f"{candidate_name}_简历.txt",
                'content': content,
                'file_hash': file_hash,
                'candidate_name': candidate_name
            }
            
        except Exception as e:
            logger.error(f"Failed to generate resume: {e}")
            raise ValueError(f"简历生成失败: {str(e)}")
    
    async def generate_batch_resumes(
        self, 
        position_data: Dict[str, Any], 
        count: int = 5
    ) -> List[Dict[str, str]]:
        count = max(1, min(20, count))
        resumes = []
        used_names = set()
        
        for _ in range(count):
            candidate_name = generate_random_name()
            while candidate_name in used_names:
                candidate_name = generate_random_name()
            used_names.add(candidate_name)
            
            try:
                resume = await self.generate_random_resume(position_data, candidate_name)
                resumes.append(resume)
            except Exception as e:
                logger.error(f"Failed to generate resume for {candidate_name}: {e}")
                continue
        
        return resumes


# 单例实例
_dev_tools_service = None


def get_dev_tools_service() -> DevToolsService:
    """获取DevToolsService单例实例"""
    global _dev_tools_service
    if _dev_tools_service is None:
        _dev_tools_service = DevToolsService()
    return _dev_tools_service
