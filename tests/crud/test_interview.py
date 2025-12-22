"""
面试会话 API 测试

验证 models → schemas → crud → api 四层能跑通
"""
import pytest
from httpx import AsyncClient
from tests.conftest import DataFactory


@pytest.mark.asyncio
async def test_interview_crud_flow(client: AsyncClient, factory: DataFactory):
    """测试面试会话完整 CRUD 流程"""
    
    # 准备数据（工厂自动创建依赖链）
    interview = await factory.create_interview()
    session_id = interview["id"]
    application_id = interview["application_id"]
    
    # 2. Read (单个)
    response = await client.get(f"/api/v1/interview/{session_id}")
    assert response.status_code == 200
    assert response.json()["data"]["application_id"] == application_id
    
    # 3. Read (列表)
    response = await client.get("/api/v1/interview")
    assert response.status_code == 200
    assert response.json()["data"]["total"] >= 1
    
    # 4. Generate questions
    questions_data = {"count": 3, "difficulty": "medium"}
    response = await client.post(f"/api/v1/interview/{session_id}/questions", json=questions_data)
    assert response.status_code == 200
    
    # 5. Sync messages
    sync_data = {
        "messages": [
            {"role": "interviewer", "content": "请自我介绍"},
            {"role": "candidate", "content": "我是测试候选人"}
        ]
    }
    response = await client.post(f"/api/v1/interview/{session_id}/sync", json=sync_data)
    assert response.status_code == 200
    
    # 6. Complete session
    response = await client.post(f"/api/v1/interview/{session_id}/complete")
    assert response.status_code == 200
    
    # 7. Delete
    response = await client.delete(f"/api/v1/interview/{session_id}")
    assert response.status_code == 200
