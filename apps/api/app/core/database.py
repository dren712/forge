from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        from sqlalchemy import text
        migrations = [
            "ALTER TABLE generations ADD COLUMN benchmark_version VARCHAR(32) DEFAULT '2.0.0'",
            "ALTER TABLE generations ADD COLUMN decision_id VARCHAR(64)",
            "ALTER TABLE mutations ADD COLUMN failure_cluster_id VARCHAR(64)",
            "ALTER TABLE mutations ADD COLUMN failure_ids JSON DEFAULT '[]'",
            "ALTER TABLE tool_memories ADD COLUMN execution_id VARCHAR(64)",
            "ALTER TABLE tool_memories ADD COLUMN failure_id VARCHAR(64)",
            "ALTER TABLE tool_memories ADD COLUMN reflection_id VARCHAR(64)",
        ]
        for mig in migrations:
            try:
                await conn.execute(text(mig))
            except Exception:
                pass
