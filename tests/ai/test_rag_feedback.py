"""
RAG 经验库集成测试

测试范围：
1. Experience CRUD API（创建、查询、删除经验）
2. 反馈学习流程（提交反馈 → 学习经验 → 存入数据库）
3. RAG 检索逻辑（Embedding粗召回 + Reranker精排 + Prompt 格式化）
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient

from app.agents.experience_manager import ExperienceManager
from app.models import AgentExperience


@pytest.fixture
def mock_embedding():
    """Mock Embedding API，避免调用 OpenAI"""
    with patch(
        "app.agents.experience_manager.ExperienceManager._get_embedding",
        new_callable=AsyncMock
    ) as mock:
        mock.return_value = [0.1] * 1536  # 返回固定的 1536 维向量
        yield mock


@pytest.fixture
def mock_reranker():
    """Mock Reranker API，避免调用 SiliconFlow"""
    with patch(
        "app.agents.experience_manager.get_reranker_client"
    ) as mock:
        mock_client = MagicMock()
        mock_client.is_configured.return_value = True
        mock_client.rerank = AsyncMock(return_value=[
            {"index": 0, "relevance_score": 0.95, "document": "doc1"},
        ])
        mock.return_value = mock_client
        yield mock_client


@pytest.mark.asyncio
async def test_experience_crud_api(client: AsyncClient, mock_embedding):
    """测试经验管理的 CRUD API"""
    
    # 1️⃣ 创建经验
    create_resp = await client.post(
        "/api/v1/feedback/experiences",
        params={
            "category": "screening",
            "learned_rule": "优先考察并发编程能力",
            "context_summary": "Python 后端岗位筛选"
        }
    )
    assert create_resp.status_code == 200
    exp_id = create_resp.json()["data"]["id"]
    
    # 2️⃣ 查询经验列表
    list_resp = await client.get("/api/v1/feedback/experiences?category=screening")
    assert list_resp.status_code == 200
    items = list_resp.json()["data"]["items"]
    assert any(item["id"] == exp_id for item in items)
    
    # 3️⃣ 删除经验
    delete_resp = await client.delete(f"/api/v1/feedback/experiences/{exp_id}")
    assert delete_resp.status_code == 200
    
    # 4️⃣ 验证已删除
    list_resp_2 = await client.get("/api/v1/feedback/experiences?category=screening")
    items_2 = list_resp_2.json()["data"]["items"]
    assert not any(item["id"] == exp_id for item in items_2)


@pytest.mark.asyncio
async def test_feedback_submission_flow(client: AsyncClient, factory, mock_embedding):
    """测试反馈学习的完整流程"""
    
    # 准备测试数据：创建一个 ScreeningTask
    task = await factory.create_screening()
    task_id = task["id"]
    
    # Mock LLM 规则提取（避免真实调用）
    expected_rule = "对于 Python 岗位，应重点考察异步编程经验"
    with patch(
        "app.agents.experience_manager.ExperienceManager._extract_rule",
        new_callable=AsyncMock
    ) as mock_extract:
        mock_extract.return_value = expected_rule
        
        # 提交反馈
        resp = await client.post(
            "/api/v1/feedback?regenerate=false",
            json={
                "category": "screening",
                "target_id": task_id,
                "feedback": "候选人虽然工作年限不足，但精通 asyncio，应该通过"
            }
        )
        
        # 验证响应
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["learned_rule"] == expected_rule
        
        # 验证数据库中存入了经验
        list_resp = await client.get("/api/v1/feedback/experiences?category=screening")
        items = list_resp.json()["data"]["items"]
        assert any(expected_rule in item["learned_rule"] for item in items)


@pytest.mark.asyncio
async def test_rag_retrieval_and_formatting(mock_embedding, mock_reranker):
    """测试 RAG 检索与 Prompt 格式化（两阶段：Embedding粗召回 + Reranker精排）"""
    
    manager = ExperienceManager()
    
    # Mock 数据库返回的经验数据
    mock_experiences = [
        AgentExperience(
            id="exp1",
            category="screening",
            context_summary="Python 后端岗位",
            learned_rule="优先考察并发编程能力",
            source_feedback="用户反馈 1",
            embedding=[0.1] * 1536  # 与查询向量一致
        ),
        AgentExperience(
            id="exp2",
            category="screening",
            context_summary="前端岗位",
            learned_rule="注重 React 经验",
            source_feedback="用户反馈 2",
            embedding=[0.0] * 1536  # 与查询向量不同
        )
    ]
    
    # 配置 Reranker mock 返回第一个经验
    mock_reranker.rerank.return_value = [
        {"index": 0, "relevance_score": 0.95, "document": "doc1"},
    ]
    
    with patch(
        "app.agents.experience_manager.experience_crud.get_all_by_category",
        new_callable=AsyncMock
    ) as mock_get_all:
        mock_get_all.return_value = mock_experiences
        
        # 执行检索
        mock_db = MagicMock()
        results = await manager.recall(
            db=mock_db,
            category="screening",
            context="Python 后端开发岗位"
        )
        
        # 验证检索结果：Reranker 精排后返回相关经验
        assert len(results) >= 1
        assert results[0].learned_rule == "优先考察并发编程能力"
        
        # 验证 Prompt 格式化
        prompt_text = manager.format_experiences_for_prompt(results)
        assert "优先考察并发编程能力" in prompt_text
