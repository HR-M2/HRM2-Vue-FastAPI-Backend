"""
岗位AI服务模块。
提供AI生成岗位要求的功能。
"""
import json
import logging
from typing import Dict, Any, List, Optional
from openai import OpenAI

from .llm_config import get_config_list, get_embedding_config

logger = logging.getLogger(__name__)


class PositionAIService:
    """AI生成岗位要求服务"""
    
    # 岗位要求的JSON结构说明
    POSITION_SCHEMA = """
{
    "position": "岗位名称（字符串）",
    "description": "岗位描述（字符串）",
    "required_skills": ["必备技能列表"],
    "optional_skills": ["可选技能列表"],
    "min_experience": 最低工作经验年数（整数）,
    "education": ["学历要求，可选值：大专、本科、硕士、博士"],
    "certifications": ["证书要求列表"],
    "salary_range": [最低月薪, 最高月薪],
    "project_requirements": {
        "min_projects": 最少项目数量（整数）,
        "team_lead_experience": 是否要求团队管理经验（布尔值）
    }
}
"""
    
    def __init__(self):
        # 获取LLM配置
        llm_config = get_config_list()[0]
        self.api_key = llm_config.get('api_key', '')
        self.base_url = llm_config.get('base_url', 'https://api.openai.com/v1')
        self.model = llm_config.get('model', 'gpt-3.5-turbo')
        self.temperature = llm_config.get('temperature', 0.7)
        self.timeout = 120
        
        # 获取Embedding配置
        embedding_config = get_embedding_config()
        self.embedding_api_key = embedding_config.get('api_key', '')
        self.embedding_base_url = embedding_config.get('base_url', '')
        self.embedding_model = embedding_config.get('model', '')
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )
    
    def generate_position_requirements(
        self, 
        description: str, 
        documents: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        根据用户输入的描述和可选的文档生成岗位要求。
        
        参数:
            description: 用户输入的岗位描述（可以是一句话或详细内容）
            documents: 可选的文档列表，每个文档包含 name 和 content
            
        返回:
            生成的岗位要求JSON
        """
        # 构建上下文
        context_parts = []
        
        if documents:
            context_parts.append("以下是参考文档内容：")
            for doc in documents:
                doc_name = doc.get('name', '未命名文档')
                doc_content = doc.get('content', '')
                if doc_content:
                    # 限制每个文档的内容长度，避免超出token限制
                    max_doc_length = 3000
                    if len(doc_content) > max_doc_length:
                        doc_content = doc_content[:max_doc_length] + "...(内容已截断)"
                    context_parts.append(f"\n--- {doc_name} ---\n{doc_content}")
        
        context = "\n".join(context_parts) if context_parts else ""
        
        # 构建prompt
        system_prompt = f"""你是一位专业的人力资源专家，擅长根据岗位描述生成结构化的招聘要求。

你需要根据用户提供的岗位描述（可能是简短的一句话，也可能是详细的需求说明），生成完整的岗位要求JSON。

输出格式必须严格遵循以下JSON结构：
{self.POSITION_SCHEMA}

注意事项：
1. 根据岗位类型合理推断所需技能、学历、经验等要求
2. 技能列表应该具体且与岗位相关
3. 薪资范围应该符合市场行情（单位：元/月）
4. 如果信息不足，使用合理的默认值
5. 只输出JSON，不要有任何其他文字说明
6. 确保JSON格式正确，可以被解析"""

        user_message = f"""请根据以下岗位描述生成招聘要求：

{description}
{context}

请直接输出JSON格式的岗位要求，不要包含任何其他内容。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=self.temperature,
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 清理可能的markdown代码块标记
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            elif result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            # 解析JSON
            position_data = json.loads(result_text)
            
            # 验证必要字段
            self._validate_position_data(position_data)
            
            return position_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"Raw response: {result_text}")
            raise ValueError(f"AI返回的结果不是有效的JSON格式: {str(e)}")
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            raise ValueError(f"AI生成失败: {str(e)}")
    
    def _validate_position_data(self, data: Dict[str, Any]) -> None:
        """验证生成的岗位数据结构"""
        required_fields = ['position']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"生成的数据缺少必要字段: {field}")
        
        # 确保数组字段是列表类型
        array_fields = ['required_skills', 'optional_skills', 'education', 'certifications']
        for field in array_fields:
            if field in data and not isinstance(data[field], list):
                data[field] = [data[field]] if data[field] else []
        
        # 确保salary_range是正确格式
        if 'salary_range' in data:
            sr = data['salary_range']
            if isinstance(sr, list) and len(sr) >= 2:
                data['salary_range'] = [int(sr[0]), int(sr[1])]
            else:
                data['salary_range'] = [0, 0]
        else:
            data['salary_range'] = [0, 0]
        
        # 确保project_requirements是正确格式
        if 'project_requirements' not in data:
            data['project_requirements'] = {
                'min_projects': 0,
                'team_lead_experience': False
            }
        elif isinstance(data['project_requirements'], dict):
            pr = data['project_requirements']
            if 'min_projects' not in pr:
                pr['min_projects'] = 0
            if 'team_lead_experience' not in pr:
                pr['team_lead_experience'] = False
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        获取文本的向量表示（用于未来的语义搜索功能）。
        
        参数:
            texts: 文本列表
            
        返回:
            向量列表
        """
        if not self.embedding_model:
            logger.warning("Embedding model not configured")
            return []
        
        try:
            embedding_client = OpenAI(
                api_key=self.embedding_api_key,
                base_url=self.embedding_base_url,
                timeout=self.timeout
            )
            
            response = embedding_client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            
            return [item.embedding for item in response.data]
            
        except Exception as e:
            logger.error(f"Failed to get embeddings: {e}")
            return []


# 单例实例
_position_ai_service = None


def get_position_ai_service() -> PositionAIService:
    """获取PositionAIService单例实例"""
    global _position_ai_service
    if _position_ai_service is None:
        _position_ai_service = PositionAIService()
    return _position_ai_service
