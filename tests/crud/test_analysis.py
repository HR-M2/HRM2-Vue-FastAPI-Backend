"""
综合分析 API 测试

验证 models → schemas → crud → api 四层能跑通

注意: 创建综合分析需要调用 AI 服务，此处只测试 Read/Delete 和直接 CRUD
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import analysis_crud
from app.schemas.analysis import ComprehensiveAnalysisCreate


async def create_application(client: AsyncClient, suffix: str = "") -> str:
    """创建测试应聘申请，返回 ID"""
    # 创建岗位
    pos_data = {
        "title": f"分析测试岗位{suffix}",
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
        "candidate_name": f"分析测试人{suffix}",
        "phone": "13800000004",
        "email": "analysis@test.com",
        "content": "分析测试简历内容",
        "file_hash": f"analysishash{suffix}",
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
async def test_analysis_crud_flow(client: AsyncClient, db_session: AsyncSession):
    """测试综合分析 CRUD 流程（绕过 AI 服务）"""
    
    # 准备数据
    application_id = await create_application(client, "analysis1")
    
    # 1. 直接通过 CRUD 创建分析记录（绕过需要 AI 的 API）
    create_schema = ComprehensiveAnalysisCreate(application_id=application_id)
    analysis_result = {
        "final_score": 78.5,
        "recommendation_level": "推荐录用",
        "recommendation_reason": "测试推荐理由",
        "suggested_action": "安排复试",
        "dimension_scores": {},
        "report": "测试报告内容",
        "input_snapshot": {"position": "测试岗位", "candidate": "测试候选人"}
    }
    analysis = await analysis_crud.create_analysis(
        db_session, obj_in=create_schema, analysis_result=analysis_result
    )
    await db_session.commit()
    analysis_id = analysis.id
    
    # 2. Read (单个) via API
    response = await client.get(f"/api/v1/analysis/{analysis_id}")
    assert response.status_code == 200
    assert response.json()["data"]["application_id"] == application_id
    
    # 3. Read (列表)
    response = await client.get("/api/v1/analysis")
    assert response.status_code == 200
    assert response.json()["data"]["total"] >= 1
    
    # 4. Delete
    response = await client.delete(f"/api/v1/analysis/{analysis_id}")
    assert response.status_code == 200
