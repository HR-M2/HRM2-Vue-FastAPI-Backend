"""
测试配置文件

提供测试用的 fixtures：内存数据库、测试客户端等
"""
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.database import Base, get_db
from app.main import create_app


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
