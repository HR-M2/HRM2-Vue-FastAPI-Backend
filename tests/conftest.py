"""
测试配置文件

提供测试用的 fixtures：内存数据库、测试客户端、测试数据工厂等
"""
import asyncio
from typing import AsyncGenerator, Optional
from dataclasses import dataclass, field

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.database import Base, get_db
from app.main import create_app


# ========== 测试数据工厂 ==========

@dataclass
class DataFactory:
    """
    测试数据工厂类
    
    集中管理测试数据创建，避免各测试文件重复代码
    字段变更时只需修改此处
    """
    client: AsyncClient
    _counter: int = field(default=0, repr=False)
    
    def _next_id(self) -> str:
        """生成唯一后缀，避免数据冲突"""
        self._counter += 1
        return str(self._counter)
    
    async def create_position(self, **overrides) -> dict:
        """创建岗位，返回完整响应数据"""
        suffix = self._next_id()
        data = {
            "title": f"测试岗位{suffix}",
            "department": "测试部",
            "description": "测试用岗位描述",
            "required_skills": ["Python", "FastAPI"],
            "optional_skills": ["Docker"],
            "min_experience": 0,
            "education": ["本科"],
            "salary_min": 10,
            "salary_max": 20,
            **overrides
        }
        resp = await self.client.post("/api/v1/positions", json=data)
        assert resp.status_code == 200, f"创建岗位失败: {resp.text}"
        return resp.json()["data"]
    
    async def create_resume(self, **overrides) -> dict:
        """创建简历，返回完整响应数据"""
        suffix = self._next_id()
        data = {
            "candidate_name": f"测试候选人{suffix}",
            "phone": f"138{suffix.zfill(8)}",
            "email": f"test{suffix}@example.com",
            "content": "测试简历内容，包含工作经历和技能描述。",
            "filename": f"resume_{suffix}.pdf",
            "file_hash": f"hash{suffix}",
            "file_size": 1024,
            "notes": "测试备注",
            **overrides
        }
        resp = await self.client.post("/api/v1/resumes", json=data)
        assert resp.status_code == 200, f"创建简历失败: {resp.text}"
        return resp.json()["data"]
    
    async def create_application(
        self, 
        position_id: Optional[str] = None, 
        resume_id: Optional[str] = None,
        **overrides
    ) -> dict:
        """创建应聘申请，自动创建依赖的岗位和简历"""
        if position_id is None:
            position = await self.create_position()
            position_id = position["id"]
        if resume_id is None:
            resume = await self.create_resume()
            resume_id = resume["id"]
        
        data = {
            "position_id": position_id,
            "resume_id": resume_id,
            "notes": "测试申请备注",
            **overrides
        }
        resp = await self.client.post("/api/v1/applications", json=data)
        assert resp.status_code == 200, f"创建申请失败: {resp.text}"
        return resp.json()["data"]
    
    async def create_screening(self, application_id: Optional[str] = None, **overrides) -> dict:
        """创建筛选任务"""
        if application_id is None:
            app = await self.create_application()
            application_id = app["id"]
        
        data = {"application_id": application_id, **overrides}
        resp = await self.client.post("/api/v1/screening", json=data)
        assert resp.status_code == 200, f"创建筛选任务失败: {resp.text}"
        return resp.json()["data"]
    
    async def create_interview(self, application_id: Optional[str] = None, **overrides) -> dict:
        """创建面试会话"""
        if application_id is None:
            app = await self.create_application()
            application_id = app["id"]
        
        data = {
            "application_id": application_id,
            "interview_type": "general",
            "config": {},
            **overrides
        }
        resp = await self.client.post("/api/v1/interview", json=data)
        assert resp.status_code == 200, f"创建面试会话失败: {resp.text}"
        return resp.json()["data"]
    
    async def create_video(self, application_id: Optional[str] = None, **overrides) -> dict:
        """创建视频分析"""
        if application_id is None:
            app = await self.create_application()
            application_id = app["id"]
        
        suffix = self._next_id()
        data = {
            "application_id": application_id,
            "video_name": f"test_video_{suffix}.mp4",
            "video_path": f"/uploads/test_video_{suffix}.mp4",
            "file_size": 10485760,
            "duration": 300,
            **overrides
        }
        resp = await self.client.post("/api/v1/video", json=data)
        assert resp.status_code == 200, f"创建视频分析失败: {resp.text}"
        return resp.json()["data"]


@pytest_asyncio.fixture
async def factory(client: AsyncClient) -> DataFactory:
    """提供测试数据工厂实例"""
    return DataFactory(client=client)


# 使用内存 SQLite 作为测试数据库
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# 创建测试引擎
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

# 创建测试会话工厂
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环（整个测试会话共享）"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    为每个测试函数提供独立的数据库会话
    
    每个测试前创建表，测试后删除表，确保测试隔离
    """
    # 创建所有表
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 提供会话
    async with TestSessionLocal() as session:
        yield session
    
    # 删除所有表
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    提供测试用的 HTTP 客户端
    
    覆盖 get_db 依赖，使用测试数据库
    """
    app = create_app()
    
    # 覆盖数据库依赖
    async def override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise
    
    app.dependency_overrides[get_db] = override_get_db
    
    # 创建异步测试客户端
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
    
    # 清理依赖覆盖
    app.dependency_overrides.clear()
