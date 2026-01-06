"""
RAG 经验学习与检索流程测试

测试目标：
1. 经验存储（API层）
2. 向量检索 Mock (模拟检索命中)
3. 经验注入 (验证 Prompt 格式化)
"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient
from typing import List

from app.agents.experience_manager import ExperienceManager, AgentExperience
from app.models import AgentExperience as AgentExperienceModel
from app.api.v1.feedback import FeedbackRequest

@pytest.fixture
def mock_embedding():
    """Mock Embedding 生成，避免调用 OpenAI"""
    with patch("app.agents.experience_manager.ExperienceManager._get_embedding", new_callable=AsyncMock) as mock:
        # 返回 1536 维的虚拟向量
        mock.return_value = [0.1] * 1536
        yield mock



@pytest.mark.asyncio
async def test_experience_crud_api(client: AsyncClient, mock_embedding):
    """测试经验管理的 CRUD API"""
    
    # 1. 创建一条手动经验
    exp_data = {
        "category": "screening",
        "learned_rule": "测试经验内容：注重考察并发编程能力",
        "context_summary": "手动添加测试"
    }
    # 注意：API 定义中使用 Query 参数接收数据
    create_resp = await client.post("/api/v1/feedback/experiences", params=exp_data)
    assert create_resp.status_code == 200, f"创建经验失败: {create_resp.text}"
    exp_id = create_resp.json()["data"]["id"]
    
    # 2. 获取列表
    list_resp = await client.get("/api/v1/feedback/experiences?category=screening")
    assert list_resp.status_code == 200
    data = list_resp.json()["data"]
    items = data["items"]
    assert len(items) >= 1
    assert any(i["id"] == exp_id for i in items)
    
    # 3. 删除经验
    del_resp = await client.delete(f"/api/v1/feedback/experiences/{exp_id}")
    assert del_resp.status_code == 200
    
    # 4. 再次获取，应为空（或不包含该ID）
    list_resp_2 = await client.get("/api/v1/feedback/experiences?category=screening")
    items_2 = list_resp_2.json()["data"]["items"]
    assert not any(i["id"] == exp_id for i in items_2)


@pytest.mark.asyncio
async def test_feedback_submission_flow(client: AsyncClient, mock_embedding, factory):
    """测试提交反馈触发经验学习"""
    
    # 准备基础数据：必须要有 ScreeningTask，因为 submit_feedback 会查 task
    screening_task = await factory.create_screening()
    task_id = screening_task["id"]
    
    # 模拟 LLM 总结出的规则
    mock_rule = "对于Python岗位，应重点考察异步编程经验"
    
    # Mock ExperienceManager.learn 方法，验证它是否被调用
    # 即使我们 Mock 了 _get_embedding，learn 内部还有 CRUD 操作
    # 为了更深层的集成测试，我们只 Mock Embedding，让 learn 真正写入 DB
    
    # 在这个测试中，我们需要 Mock LLMClient.complete 来模拟“从反馈中总结规则”的步骤
    # 因为 submit_feedback 内部会调用 LLM 总结 rule
    # 在这个测试中，我们直接 Mock _extract_rule，规避 LLMClient 单例问题
    # 这样 Manager 不需要调用 LLM，直接返回我们指定的 Rule
    with patch("app.agents.experience_manager.ExperienceManager._extract_rule", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = mock_rule
        
        # 提交反馈：Payload 必须匹配 FeedbackRequest
        feedback_data = {
            "category": "screening",
            "target_id": task_id,
            "feedback": "即使工作年限不够，但如果精通 asyncio 也可以通过。原评分低了。"
        }
        
        # regenerate=False 以避免并在重生成报告时再次调用 LLM (简化测试)
        resp = await client.post("/api/v1/feedback?regenerate=False", json=feedback_data)
        assert resp.status_code == 200, f"提交反馈失败: {resp.text}"
        
        # 验证返回
        data = resp.json()["data"]
        assert "learned_rule" in data
        assert data["learned_rule"] == mock_rule
        
        # 验证数据库中确实存入了经验
        # 通过 API 查
        list_resp = await client.get("/api/v1/feedback/experiences?category=screening")
        data = list_resp.json()["data"]
        items = data["items"]  # 修正获取路径
        # 即使 Mock 了 Embedding，内容应该还是存进去了
        assert any(mock_rule in i["learned_rule"] for i in items)  # i["rule"] -> i["learned_rule"]


@pytest.mark.asyncio
async def test_rag_retrieval_logic(mock_embedding):
    """测试 RAG 检索与 Prompt 格式化逻辑 (单元测试层面)"""
    
    manager = ExperienceManager()
    
    # 手动设置 mock embedding 的返回值，模拟不同向量
    # 注意：cosine_similarity 需要 numpy 或手动计算，这里我们简化
    # 假设 recall 内部计算逻辑正确，我们重点测试 '如果有数据，是否能跑通'
    # 或者我们 mock experience_crud.get_all_by_category 来返回预设数据
    
    mock_embedding.return_value = [0.1] * 1536
    
    with patch("app.agents.experience_manager.experience_crud.get_all_by_category", new_callable=AsyncMock) as mock_get_all:
        from app.models import AgentExperience
        
        # 1. 模拟数据库返回的经验列表
        mock_experiences = [
            AgentExperience(
                id="1",
                category="screening",
                content="上下文内容...",
                learned_rule="规则1: 重视并发经验",
                source_feedback="feedback1",
                embedding=[0.1] * 1536, # 与查询向量完全相同 -> 相似度 1.0
                created_at="2023-01-01"
            ),
            AgentExperience(
                id="2",
                category="screening",
                content="上下文...",
                learned_rule="规则2: 忽略学历",
                source_feedback="feedback2",
                embedding=[0.0] * 1536, # 完全不同 -> 相似度 0 (假设)
                created_at="2023-01-02"
            )
        ]
        mock_get_all.return_value = mock_experiences
        
        # 为了让 cosine_similarity 不报错，我们需要 mock 它，或者确保 embedding 是合法列表
        # 这里我们直接透传，相信 app.core.embedding.cosine_similarity 能处理 list
        
        # 2. 执行 recall
        results = await manager.recall(db=None, category="screening", context="Python 岗位")
        
        # 验证结果
        assert len(results) >= 1
        # 因为 mock_exp[0] 的向量与 mock_embedding 返回值完全一致，它应该排在第一
        assert results[0].learned_rule == "规则1: 重视并发经验"
        
        # 3. 测试 Prompt 格式化
        prompt_text = manager.format_experiences_for_prompt(results)
        
        assert "历史经验参考" in prompt_text or "经验" in prompt_text # 根据具体配置可能有变
        assert "规则1: 重视并发经验" in prompt_text
