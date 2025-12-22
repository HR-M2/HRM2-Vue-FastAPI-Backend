"""
简历筛选 API 测试

验证 models → schemas → crud → api 四层能跑通
"""
import pytest
from httpx import AsyncClient
from tests.conftest import DataFactory


@pytest.mark.asyncio
async def test_screening_crud_flow(client: AsyncClient, factory: DataFactory):
    """测试筛选任务完整 CRUD 流程"""
    
    # 准备数据（工厂自动创建依赖链）
    application = await factory.create_application()
    application_id = application["id"]
    
    # 1. Create
    create_data = {"application_id": application_id}
    response = await client.post("/api/v1/screening", json=create_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    task_id = data["data"]["id"]
    
    # 2. Read (单个)
    response = await client.get(f"/api/v1/screening/{task_id}")
    assert response.status_code == 200
    assert response.json()["data"]["application_id"] == application_id
    
    # 3. Read (列表)
    response = await client.get("/api/v1/screening")
    assert response.status_code == 200
    assert response.json()["data"]["total"] >= 1
    
    # 4. Get status
    response = await client.get(f"/api/v1/screening/{task_id}/status")
    assert response.status_code == 200
    assert "status" in response.json()["data"]
    
    # 5. Update result
    update_data = {
        "status": "completed",
        "score": 85.0,
        "summary": "测试总结",
        "recommendation": "recommend"
    }
    response = await client.patch(f"/api/v1/screening/{task_id}", json=update_data)
    assert response.status_code == 200
    
    # 6. Delete
    response = await client.delete(f"/api/v1/screening/{task_id}")
    assert response.status_code == 200
