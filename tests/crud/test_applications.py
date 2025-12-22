"""
应聘申请 API 测试

验证 models → schemas → crud → api 四层能跑通
"""
import pytest
from httpx import AsyncClient
from tests.conftest import DataFactory


@pytest.mark.asyncio
async def test_application_crud_flow(client: AsyncClient, factory: DataFactory):
    """测试应聘申请完整 CRUD 流程"""
    
    # 准备数据（工厂自动创建依赖的岗位和简历）
    position = await factory.create_position()
    resume = await factory.create_resume()
    
    # 1. Create
    application = await factory.create_application(
        position_id=position["id"],
        resume_id=resume["id"]
    )
    application_id = application["id"]
    
    # 2. Read (单个)
    response = await client.get(f"/api/v1/applications/{application_id}")
    assert response.status_code == 200
    assert response.json()["data"]["position_id"] == position["id"]
    
    # 3. Read (列表 - 按 position_id 筛选，避免惰性加载问题)
    response = await client.get("/api/v1/applications", params={"position_id": position["id"]})
    assert response.status_code == 200
    assert response.json()["data"]["total"] >= 1
    
    # 4. Stats overview
    response = await client.get("/api/v1/applications/stats/overview")
    assert response.status_code == 200
    assert "total" in response.json()["data"]
    
    # 5. Update
    update_data = {"notes": "更新后的备注"}
    response = await client.patch(f"/api/v1/applications/{application_id}", json=update_data)
    assert response.status_code == 200
    
    # 6. Delete (soft delete)
    response = await client.delete(f"/api/v1/applications/{application_id}")
    assert response.status_code == 200
