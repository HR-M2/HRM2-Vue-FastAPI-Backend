"""
视频分析 API 测试

验证 models → schemas → crud → api 四层能跑通
"""
import pytest
from httpx import AsyncClient
from tests.conftest import DataFactory


@pytest.mark.asyncio
async def test_video_crud_flow(client: AsyncClient, factory: DataFactory):
    """测试视频分析完整 CRUD 流程"""
    
    # 准备数据（工厂自动创建依赖链）
    video = await factory.create_video()
    video_id = video["id"]
    application_id = video["application_id"]
    
    # 2. Read (单个)
    response = await client.get(f"/api/v1/video/{video_id}")
    assert response.status_code == 200
    assert response.json()["data"]["application_id"] == application_id
    
    # 3. Read (列表)
    response = await client.get("/api/v1/video")
    assert response.status_code == 200
    assert response.json()["data"]["total"] >= 1
    
    # 4. Get status
    response = await client.get(f"/api/v1/video/{video_id}/status")
    assert response.status_code == 200
    assert "status" in response.json()["data"]
    
    # 5. Update result
    update_data = {
        "status": "completed",
        "openness": 75.0,
        "conscientiousness": 80.0,
        "extraversion": 70.0,
        "agreeableness": 85.0,
        "neuroticism": 30.0,
        "confidence_score": 0.9,
        "summary": "测试分析摘要"
    }
    response = await client.patch(f"/api/v1/video/{video_id}", json=update_data)
    assert response.status_code == 200
    
    # 6. Delete
    response = await client.delete(f"/api/v1/video/{video_id}")
    assert response.status_code == 200
