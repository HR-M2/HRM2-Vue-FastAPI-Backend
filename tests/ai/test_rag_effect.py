# -*- coding: utf-8 -*-
"""
RAG 效果测试（真实 API 调用）

测试 RAG 两阶段检索的实际效果：
1. 跨岗位借鉴：Python后端能召回"后端通用"经验
2. 互相排除：厨师查询不会召回技术岗位经验  
3. 通用经验：通用经验能被正确召回

运行方式：
    pytest tests/ai/test_rag_effect.py -v -s
    pytest -m rag_effect -v -s

注意：此测试会调用真实的 Embedding 和 Reranker API，需要配置 .env
"""
import pytest
from dataclasses import dataclass, field
from typing import List, Dict
from unittest.mock import MagicMock, AsyncMock

from app.core.embedding import get_embedding_client, cosine_similarity
from app.core.reranker import get_reranker_client
from app.agents.experience_manager import ExperienceManager
from app.models import AgentExperience


# ============================================================
# 测试数据
# ============================================================
@dataclass
class SampleExperience:
    """样本经验数据"""
    id: str
    learned_rule: str
    context_summary: str
    job_type: str  # 仅用于评估标记


@dataclass
class SampleQuery:
    """样本查询"""
    text: str
    target_job: str
    expected_ids: List[str] = field(default_factory=list)  # 期望召回
    unexpected_ids: List[str] = field(default_factory=list)  # 期望不召回


# 测试经验库
SAMPLE_EXPERIENCES = [
    # === Java 后端 ===
    SampleExperience("java_1", 
        "面试Java开发候选人时，应重点追问分布式系统实战经验，包括服务拆分、数据一致性、限流熔断等场景",
        "Java后端开发工程师面试评估", "Java后端"),
    SampleExperience("java_2",
        "Java候选人如果能清晰解释JVM内存模型和GC调优经验，说明基础扎实，应加分",
        "Java后端开发工程师技术面试", "Java后端"),
    
    # === Python 后端 ===
    SampleExperience("python_1",
        "Python后端候选人应熟悉异步编程模型，如asyncio的使用和原理",
        "Python后端开发工程师技术面试", "Python后端"),
    SampleExperience("python_2",
        "考察Python工程师时，关注其对Django/FastAPI等框架的理解深度",
        "Python后端开发工程师框架能力", "Python后端"),
    
    # === 后端通用（Java/Python/Go 都适用）===
    SampleExperience("backend_1",
        "后端开发候选人应能清晰描述数据库优化经验，包括索引设计、慢查询分析",
        "后端开发数据库能力", "后端通用"),
    SampleExperience("backend_2",
        "考察后端工程师的API设计能力，RESTful规范和接口版本管理是基础",
        "后端开发API设计", "后端通用"),
    SampleExperience("backend_3",
        "后端候选人对微服务架构的理解很重要，包括服务发现、配置中心、链路追踪",
        "后端开发微服务能力", "后端通用"),
    
    # === 厨师（完全不相关）===
    SampleExperience("chef_1",
        "面试厨师时，首先做的菜要好吃，色香味俱全是基本要求",
        "厨师岗位面试评估", "厨师"),
    SampleExperience("chef_2",
        "厨师候选人应展示对食材新鲜度的判断能力，这是专业素养的体现",
        "厨师食材判断能力", "厨师"),
    
    # === 通用经验（所有岗位适用）===
    SampleExperience("general_1",
        "在时间受限的面试中，能精准聚焦重点并辅以数据支撑的回答，应获得更高评分",
        "面试时间管理", "通用"),
    SampleExperience("general_2",
        "候选人展现出的学习能力和成长潜力，有时比当前技能水平更重要",
        "候选人潜力评估", "通用"),
]

# 测试查询
SAMPLE_QUERIES = [
    # Java 后端查询 - 期望召回 Java专用 + 后端通用，不召回厨师
    SampleQuery(
        "Java后端开发工程师 面试评估", 
        "Java后端",
        expected_ids=["java_1", "java_2", "backend_1", "backend_2", "backend_3"],
        unexpected_ids=["chef_1", "chef_2"]
    ),
    
    # Python 后端查询 - 期望召回 Python专用 + 后端通用，不召回厨师
    SampleQuery(
        "Python后端开发工程师 面试评估",
        "Python后端", 
        expected_ids=["python_1", "python_2", "backend_1", "backend_2", "backend_3"],
        unexpected_ids=["chef_1", "chef_2"]
    ),
    
    # 厨师查询 - 只召回厨师相关，不召回技术岗位
    SampleQuery(
        "厨师岗位候选人 面试评估",
        "厨师",
        expected_ids=["chef_1", "chef_2"],
        unexpected_ids=["java_1", "java_2", "python_1", "python_2", "backend_1", "backend_2", "backend_3"]
    ),
]


# ============================================================
# 辅助函数
# ============================================================
def create_mock_experience(sample_exp: SampleExperience, embedding: List[float]) -> AgentExperience:
    """创建 AgentExperience 对象"""
    return AgentExperience(
        id=sample_exp.id,
        category="interview",
        learned_rule=sample_exp.learned_rule,
        context_summary=sample_exp.context_summary,
        source_feedback=f"[测试数据] {sample_exp.job_type}",
        embedding=embedding,
    )


def evaluate_results(query: SampleQuery, result_ids: List[str]) -> Dict:
    """评估检索结果"""
    # 期望召回的命中数
    expected_hits = set(result_ids) & set(query.expected_ids)
    expected_recall = len(expected_hits) / len(query.expected_ids) if query.expected_ids else 1.0
    
    # 不期望召回的误召数
    unexpected_hits = set(result_ids) & set(query.unexpected_ids)
    no_contamination = len(unexpected_hits) == 0
    
    return {
        "expected_recall": expected_recall,
        "expected_hits": list(expected_hits),
        "expected_misses": list(set(query.expected_ids) - set(result_ids)),
        "no_contamination": no_contamination,
        "unexpected_hits": list(unexpected_hits),
        "result_ids": result_ids,
    }


# ============================================================
# 测试用例
# ============================================================
@pytest.mark.rag_effect
@pytest.mark.asyncio
class TestRAGEffect:
    """RAG 效果测试类"""
    
    @pytest.fixture
    async def embedding_client(self):
        """获取 Embedding 客户端"""
        client = get_embedding_client()
        if not client.is_configured():
            pytest.skip("Embedding API 未配置，跳过 RAG 效果测试")
        return client
    
    @pytest.fixture
    async def reranker_client(self):
        """获取 Reranker 客户端"""
        client = get_reranker_client()
        if not client.is_configured():
            pytest.skip("Reranker API 未配置，跳过 RAG 效果测试")
        return client
    
    @pytest.fixture
    async def indexed_experiences(self, embedding_client) -> List[AgentExperience]:
        """构建带向量的经验列表"""
        experiences = []
        for sample_exp in SAMPLE_EXPERIENCES:
            content = f"{sample_exp.context_summary}\n{sample_exp.learned_rule}"
            embedding = await embedding_client.embed(content)
            exp = create_mock_experience(sample_exp, embedding)
            experiences.append(exp)
        return experiences

    async def test_java_backend_retrieval(self, embedding_client, reranker_client, indexed_experiences):
        """
        测试 Java 后端查询的召回效果
        
        期望：
        - 召回 Java 专用经验
        - 召回后端通用经验（数据库、API、微服务）
        - 不召回厨师经验
        """
        query = SAMPLE_QUERIES[0]  # Java后端查询
        
        # 1. Embedding 粗召回
        query_embedding = await embedding_client.embed(query.text)
        scored = []
        for exp in indexed_experiences:
            score = cosine_similarity(query_embedding, exp.embedding)
            scored.append((score, exp))
        scored.sort(key=lambda x: x[0], reverse=True)
        candidates = scored[:10]
        
        print(f"\n{'='*60}")
        print(f"🔍 查询: {query.text}")
        print(f"   目标岗位: {query.target_job}")
        print(f"\n📊 Stage 1 - Embedding 粗召回 (Top 10):")
        for score, exp in candidates:
            job_type = next((t.job_type for t in SAMPLE_EXPERIENCES if t.id == exp.id), "未知")
            tag = "✅" if exp.id in query.expected_ids else ("❌" if exp.id in query.unexpected_ids else "⚪")
            print(f"   [{score:.3f}] {tag} [{job_type}] {exp.learned_rule[:40]}...")
        
        # 2. Reranker 精排
        documents = [f"{exp.context_summary}\n{exp.learned_rule}" for _, exp in candidates]
        rerank_results = await reranker_client.rerank(query.text, documents, top_n=5)
        
        print(f"\n📊 Stage 2 - Reranker 精排 (Top 5):")
        final_ids = []
        for r in rerank_results:
            idx = r["index"]
            score = r["relevance_score"]
            exp = candidates[idx][1]
            job_type = next((t.job_type for t in SAMPLE_EXPERIENCES if t.id == exp.id), "未知")
            tag = "✅" if exp.id in query.expected_ids else ("❌" if exp.id in query.unexpected_ids else "⚪")
            filtered = "" if score >= 0.2 else " [已过滤]"
            print(f"   [{score:.4f}] {tag} [{job_type}] {exp.learned_rule[:40]}...{filtered}")
            if score >= 0.2:
                final_ids.append(exp.id)
        
        # 3. 评估
        metrics = evaluate_results(query, final_ids)
        print(f"\n📈 评估:")
        print(f"   期望召回率: {metrics['expected_recall']*100:.1f}%")
        print(f"   命中: {metrics['expected_hits']}")
        print(f"   未命中: {metrics['expected_misses']}")
        contamination_msg = "✅" if metrics['no_contamination'] else f"❌ 误召: {metrics['unexpected_hits']}"
        print(f"   无污染: {contamination_msg}")
        
        # 断言
        assert metrics['no_contamination'], f"不应召回厨师经验，但召回了: {metrics['unexpected_hits']}"
        assert metrics['expected_recall'] >= 0.4, f"期望召回率应 >= 40%，实际: {metrics['expected_recall']*100:.1f}%"

    async def test_python_backend_retrieval(self, embedding_client, reranker_client, indexed_experiences):
        """
        测试 Python 后端查询的召回效果
        
        关键验证：能否召回"后端通用"经验（数据库优化、微服务等）
        """
        query = SAMPLE_QUERIES[1]  # Python后端查询
        
        # 1. Embedding 粗召回
        query_embedding = await embedding_client.embed(query.text)
        scored = []
        for exp in indexed_experiences:
            score = cosine_similarity(query_embedding, exp.embedding)
            scored.append((score, exp))
        scored.sort(key=lambda x: x[0], reverse=True)
        candidates = scored[:10]
        
        print(f"\n{'='*60}")
        print(f"🔍 查询: {query.text}")
        print(f"   目标岗位: {query.target_job}")
        print(f"\n📊 Stage 1 - Embedding 粗召回 (Top 10):")
        for score, exp in candidates:
            job_type = next((t.job_type for t in SAMPLE_EXPERIENCES if t.id == exp.id), "未知")
            tag = "✅" if exp.id in query.expected_ids else ("❌" if exp.id in query.unexpected_ids else "⚪")
            print(f"   [{score:.3f}] {tag} [{job_type}] {exp.learned_rule[:40]}...")
        
        # 2. Reranker 精排
        documents = [f"{exp.context_summary}\n{exp.learned_rule}" for _, exp in candidates]
        rerank_results = await reranker_client.rerank(query.text, documents, top_n=5)
        
        print(f"\n📊 Stage 2 - Reranker 精排 (Top 5):")
        final_ids = []
        for r in rerank_results:
            idx = r["index"]
            score = r["relevance_score"]
            exp = candidates[idx][1]
            job_type = next((t.job_type for t in SAMPLE_EXPERIENCES if t.id == exp.id), "未知")
            tag = "✅" if exp.id in query.expected_ids else ("❌" if exp.id in query.unexpected_ids else "⚪")
            filtered = "" if score >= 0.2 else " [已过滤]"
            print(f"   [{score:.4f}] {tag} [{job_type}] {exp.learned_rule[:40]}...{filtered}")
            if score >= 0.2:
                final_ids.append(exp.id)
        
        # 3. 评估
        metrics = evaluate_results(query, final_ids)
        print(f"\n📈 评估:")
        print(f"   期望召回率: {metrics['expected_recall']*100:.1f}%")
        print(f"   命中: {metrics['expected_hits']}")
        print(f"   未命中: {metrics['expected_misses']}")
        contamination_msg = "✅" if metrics['no_contamination'] else f"❌ 误召: {metrics['unexpected_hits']}"
        print(f"   无污染: {contamination_msg}")
        
        # 断言
        assert metrics['no_contamination'], f"不应召回厨师经验，但召回了: {metrics['unexpected_hits']}"
        # Python 查询应该能召回一些后端通用经验
        backend_hits = [id for id in final_ids if id.startswith("backend_")]
        print(f"   后端通用经验命中: {backend_hits}")

    async def test_chef_retrieval_no_tech_contamination(self, embedding_client, reranker_client, indexed_experiences):
        """
        测试厨师查询不会召回技术岗位经验
        
        这是最关键的"互相排除"测试
        """
        query = SAMPLE_QUERIES[2]  # 厨师查询
        
        # 1. Embedding 粗召回
        query_embedding = await embedding_client.embed(query.text)
        scored = []
        for exp in indexed_experiences:
            score = cosine_similarity(query_embedding, exp.embedding)
            scored.append((score, exp))
        scored.sort(key=lambda x: x[0], reverse=True)
        candidates = scored[:10]
        
        print(f"\n{'='*60}")
        print(f"🔍 查询: {query.text}")
        print(f"   目标岗位: {query.target_job}")
        print(f"\n📊 Stage 1 - Embedding 粗召回 (Top 10):")
        for score, exp in candidates:
            job_type = next((t.job_type for t in SAMPLE_EXPERIENCES if t.id == exp.id), "未知")
            tag = "✅" if exp.id in query.expected_ids else ("❌" if exp.id in query.unexpected_ids else "⚪")
            print(f"   [{score:.3f}] {tag} [{job_type}] {exp.learned_rule[:40]}...")
        
        # 2. Reranker 精排
        documents = [f"{exp.context_summary}\n{exp.learned_rule}" for _, exp in candidates]
        rerank_results = await reranker_client.rerank(query.text, documents, top_n=5)
        
        print(f"\n📊 Stage 2 - Reranker 精排 (Top 5):")
        final_ids = []
        for r in rerank_results:
            idx = r["index"]
            score = r["relevance_score"]
            exp = candidates[idx][1]
            job_type = next((t.job_type for t in SAMPLE_EXPERIENCES if t.id == exp.id), "未知")
            tag = "✅" if exp.id in query.expected_ids else ("❌" if exp.id in query.unexpected_ids else "⚪")
            filtered = "" if score >= 0.2 else " [已过滤]"
            print(f"   [{score:.4f}] {tag} [{job_type}] {exp.learned_rule[:40]}...{filtered}")
            if score >= 0.2:
                final_ids.append(exp.id)
        
        # 3. 评估
        metrics = evaluate_results(query, final_ids)
        print(f"\n📈 评估:")
        print(f"   期望召回率: {metrics['expected_recall']*100:.1f}%")
        print(f"   命中: {metrics['expected_hits']}")
        contamination_msg = "✅" if metrics['no_contamination'] else f"❌ 误召: {metrics['unexpected_hits']}"
        print(f"   无污染: {contamination_msg}")
        
        # 断言：厨师查询不应召回任何技术岗位经验
        assert metrics['no_contamination'], f"厨师查询不应召回技术经验，但召回了: {metrics['unexpected_hits']}"
        # 应该召回厨师相关经验
        chef_hits = [id for id in final_ids if id.startswith("chef_")]
        assert len(chef_hits) >= 1, "厨师查询应至少召回1条厨师经验"
        print(f"   厨师经验命中: {chef_hits}")
