"""
面试会话 API 测试

验证 models → schemas → crud → api 四层能跑通
"""
import pytest
from httpx import AsyncClient


async def create_application(client: AsyncClient, suffix: str = "") -> str:
    """创建测试应聘申请，返回 ID"""
    # 创建岗位
    pos_data = {
        "title": f"面试测试岗位{suffix}",
        "department": "测试部",
        "description": "测试用",
        "required_skills": ["Python"],
        "min_experience": 0,
        "salary_min": 10,
        "salary_max": 20
    }
    pos_resp = await client.post("/api/v1/positions", json=pos_data)
    position_id = pos_resp.json()["data"]["id"]
    
    # 创建简历
    resume_data = {
        "candidate_name": f"面试测试人{suffix}",
        "phone": "13800000002",
        "email": "interview@test.com",
        "content": "面试测试简历内容",
        "file_hash": f"interviewhash{suffix}",
        "file_size": 512
    }
    resume_resp = await client.post("/api/v1/resumes", json=resume_data)
    resume_id = resume_resp.json()["data"]["id"]
    
    # 创建申请
    app_data = {
        "position_id": position_id,
        "resume_id": resume_id
    }
    app_resp = await client.post("/api/v1/applications", json=app_data)
    return app_resp.json()["data"]["id"]


@pytest.mark.asyncio
async def test_interview_crud_flow(client: AsyncClient):
    """测试面试会话完整 CRUD 流程"""
    
    # 准备数据
    application_id = await create_application(client, "interview1")
    
    # 1. Create
    create_data = {
        "application_id": application_id,
        "interview_type": "general",
        "config": {}
    }
    response = await client.post("/api/v1/interview", json=create_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    session_id = data["data"]["id"]
    
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
