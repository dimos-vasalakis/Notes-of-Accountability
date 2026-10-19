from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings



def _connect_args(url: str) -> dict[str, Any]:
    # Supabase's transaction-mode pooler (port 6543) hands each statement to a
    # different backend, so asyncpg's prepared statements must be disabled.
    if ":6543/" in url:
        return {
            "statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
        }
    return {}


engine = create_async_engine(
    settings.database_url,
    echo=(settings.environment == "development"),
    connect_args=_connect_args(settings.database_url),
)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
