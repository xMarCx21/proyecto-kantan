"""Configuración y fixtures compartidos de Pytest."""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB_FILE = Path(__file__).parent / "test_kantan.db"
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE.as_posix()}"

from app.db import Base
from app.db.session import get_db
from app.main import app

# Motor exclusivo para pruebas apuntando a archivo temporal limpio
test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    """Limpia y recrea el esquema en cada test para asegurar aislamiento total."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP asíncrono para probar los endpoints de FastAPI."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestingSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
