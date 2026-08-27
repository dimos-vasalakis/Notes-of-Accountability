import asyncio
import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.db import get_db
from app.main import app
from app.models import Base

TEST_DATABASE_URL = settings.test_database_url or settings.database_url


@pytest.fixture(scope="session", autouse=True)
def _create_schema() -> None:
    async def _run() -> None:
        engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_run())


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    connection = await engine.connect()
    transaction = await connection.begin()

    session_maker = async_sessionmaker(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    session = session_maker()

    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
        await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    # https:// (not http://) so httpx's cookie jar stores and replays
    # Secure-flagged cookies regardless of the developer's local
    # COOKIE_SECURE setting -- ASGITransport never actually uses TLS, so
    # this is just about satisfying the cookie jar's scheme check.
    #
    # A unique X-Real-IP per test gives each one its own RateLimitMiddleware
    # bucket. The limiter is per-process and in-memory, so without this every
    # test shares one 100-req/60s budget and later tests start getting 429s
    # purely because earlier ones ran. The middleware still runs -- it's
    # exercised directly in test_middleware.py.
    async with AsyncClient(
        transport=transport,
        base_url="https://test",
        headers={"x-real-ip": f"10.0.0.{uuid.uuid4().int % 256}-{uuid.uuid4()}"},
    ) as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
