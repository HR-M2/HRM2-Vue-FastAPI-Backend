"""
简历管理 API 测试

验证 models → schemas → crud → api 四层能跑通
"""
import pytest
from httpx import AsyncClient
from tests.conftest import DataFactory


@pytest.mark.asyncio
async def test_resume_crud_flow(client: AsyncClient, factory: DataFactory):
    """测试简历完整 CRUD 流程"""
    
    # 1. Create (通过工厂创建，自定义部分字段)
    resume = await factory.create_resume(
        candidate_name="张三",
        file_hash="abc123hash"
    )
    resume_id = resume["id"]
    
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
