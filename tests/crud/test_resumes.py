"""
简历管理 API 测试

验证 models → schemas → crud → api 四层能跑通
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_resume_crud_flow(client: AsyncClient):
    """测试简历完整 CRUD 流程"""
    
    # 1. Create
    create_data = {
        "candidate_name": "张三",
        "phone": "13800138000",
        "email": "zhangsan@test.com",
        "content": "这是一份测试简历内容",
        "filename": "zhangsan_resume.pdf",
        "file_hash": "abc123hash",
        "file_size": 1024,
        "notes": "测试备注"
    }
    response = await client.post("/api/v1/resumes", json=create_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    resume_id = data["data"]["id"]
    
    # 2. Read (单个)
    response = await client.get(f"/api/v1/resumes/{resume_id}")
    assert response.status_code == 200
    assert response.json()["data"]["candidate_name"] == "张三"
    
    # 3. Read (列表)
    response = await client.get("/api/v1/resumes")
    assert response.status_code == 200
    assert response.json()["data"]["total"] >= 1
    
    # 4. Check hash
    response = await client.get("/api/v1/resumes/check-hash", params={"file_hash": "abc123hash"})
    assert response.status_code == 200
    assert response.json()["data"]["exists"] is True
    
    # 5. Update
    update_data = {"candidate_name": "张三丰", "notes": "更新后的备注"}
    response = await client.patch(f"/api/v1/resumes/{resume_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["data"]["candidate_name"] == "张三丰"
    
    # 6. Delete
    response = await client.delete(f"/api/v1/resumes/{resume_id}")
    assert response.status_code == 200
