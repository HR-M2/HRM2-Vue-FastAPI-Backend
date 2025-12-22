"""
视频分析 API 测试

验证 models → schemas → crud → api 四层能跑通
"""
import pytest
from httpx import AsyncClient


async def create_application(client: AsyncClient, suffix: str = "") -> str:
    """创建测试应聘申请，返回 ID"""
    # 创建岗位
    pos_data = {
        "title": f"视频测试岗位{suffix}",
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
        "candidate_name": f"视频测试人{suffix}",
        "phone": "13800000003",
        "email": "video@test.com",
        "content": "视频测试简历内容",
        "file_hash": f"videohash{suffix}",
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
async def test_video_crud_flow(client: AsyncClient):
    """测试视频分析完整 CRUD 流程"""
    
    # 准备数据
    application_id = await create_application(client, "video1")
    
    # 1. Create
    create_data = {
        "application_id": application_id,
        "video_name": "test_video.mp4",
        "video_path": "/uploads/test_video.mp4",
        "file_size": 10485760,
        "duration": 300
    }
    response = await client.post("/api/v1/video", json=create_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    video_id = data["data"]["id"]
    
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
