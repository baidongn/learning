"""LangGraph Checkpointer 工厂。

单元测试使用内存实现；本地和生产运行使用 PostgreSQL 实现。
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from highway_agent.config import Settings


def to_psycopg_uri(database_url: str) -> str:
    """Checkpointer 使用 psycopg3，移除 SQLAlchemy 的 asyncpg 驱动标识。"""

    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


@asynccontextmanager
async def postgres_checkpointer(database_url: str) -> AsyncIterator[AsyncPostgresSaver]:
    """创建并初始化 PostgreSQL Checkpointer 表。"""

    async with AsyncPostgresSaver.from_conn_string(to_psycopg_uri(database_url)) as saver:
        await saver.setup()
        yield saver


@asynccontextmanager
async def configured_checkpointer(
    settings: Settings,
) -> AsyncIterator[AsyncPostgresSaver | InMemorySaver]:
    """Mock 默认内存；部署显式选择 postgres 后保存可恢复状态。"""

    if settings.checkpoint_backend == "postgres":
        async with postgres_checkpointer(settings.database_url) as saver:
            yield saver
        return
    yield InMemorySaver()
