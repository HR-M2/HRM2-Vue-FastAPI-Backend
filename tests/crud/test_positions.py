"""
岗位管理 API 测试

验证 models → schemas → crud → api 四层能跑通
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_position_crud_flow(client: AsyncClient):
    """测试岗位完整 CRUD 流程"""
    
    # 1. Create
    create_data = {
        "title": "测试岗位",
        "department": "技术部",
        "description": "测试用岗位描述",
        "required_skills": ["Python", "FastAPI"],
        "optional_skills": ["Docker"],
        "min_experience": 2,
        "education": ["本科"],
        "salary_min": 15,
        "salary_max": 25
    }
    response = await client.post("/api/v1/positions", json=create_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    position_id = data["data"]["id"]
    
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
