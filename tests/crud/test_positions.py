"""
岗位管理 API 测试

验证 models → schemas → crud → api 四层能跑通
"""
import pytest
from httpx import AsyncClient
from tests.conftest import DataFactory


@pytest.mark.asyncio
async def test_position_crud_flow(client: AsyncClient, factory: DataFactory):
    """测试岗位完整 CRUD 流程"""
    
    # 1. Create (通过工厂创建)
    position = await factory.create_position(title="测试岗位")
    position_id = position["id"]
    
    # 2. Read (单个)
    response = await client.get(f"/api/v1/positions/{position_id}")
    assert response.status_code == 200
    assert response.json()["data"]["title"] == "测试岗位"
    
    # 3. Read (列表)
    response = await client.get("/api/v1/positions")
    assert response.status_code == 200
    assert response.json()["data"]["total"] >= 1
    
    # 4. Update
    update_data = {"title": "更新后的岗位", "is_active": False}
    response = await client.patch(f"/api/v1/positions/{position_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["data"]["title"] == "更新后的岗位"
    
    # 5. Delete
    response = await client.delete(f"/api/v1/positions/{position_id}")
    assert response.status_code == 200
