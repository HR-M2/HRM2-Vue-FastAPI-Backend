"""
应聘申请 API 测试

验证 models → schemas → crud → api 四层能跑通
"""
import pytest
from httpx import AsyncClient


async def create_position(client: AsyncClient) -> str:
    """创建测试岗位，返回 ID"""
    data = {
        "title": "应聘测试岗位",
        "department": "测试部",
        "description": "测试用",
        "required_skills": ["Python"],
        "min_experience": 0,
        "salary_min": 10,
        "salary_max": 20
    }
    response = await client.post("/api/v1/positions", json=data)
    return response.json()["data"]["id"]


async def create_resume(client: AsyncClient, hash_suffix: str = "") -> str:
    """创建测试简历，返回 ID"""
    data = {
        "candidate_name": "测试候选人",
        "phone": "13900139000",
        "email": "test@test.com",
        "content": "测试简历内容",
        "file_hash": f"testhash{hash_suffix}",
        "file_size": 512
    }
    response = await client.post("/api/v1/resumes", json=data)
    return response.json()["data"]["id"]


@pytest.mark.asyncio
async def test_application_crud_flow(client: AsyncClient):
    """测试应聘申请完整 CRUD 流程"""
    
    # 准备数据
    position_id = await create_position(client)
    resume_id = await create_resume(client)
    
    # 1. Create
    create_data = {
        "position_id": position_id,
        "resume_id": resume_id,
        "notes": "测试申请备注"
    }
    response = await client.post("/api/v1/applications", json=create_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    application_id = data["data"]["id"]
    
    # 2. Read (单个)
    response = await client.get(f"/api/v1/applications/{application_id}")
    assert response.status_code == 200
    assert response.json()["data"]["position_id"] == position_id
    
    # 3. Read (列表 - 按 position_id 筛选，避免惰性加载问题)
    response = await client.get("/api/v1/applications", params={"position_id": position_id})
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
