from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Normalize PostgreSQL connection schemes for asyncpg
db_url = settings.database_url
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+asyncpg://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

connect_args = {}
engine_kwargs = {"echo": False}

if "sqlite" in db_url:
    connect_args["check_same_thread"] = False
else:
    engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,
    })
    # Supabase Transaction Pooler (port 6543) compatibility
    if ":6543" in db_url:
        connect_args["statement_cache_size"] = 0

engine = create_async_engine(
    db_url,
    connect_args=connect_args,
    **engine_kwargs,
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
        # SQLite local backward-compatibility migrations
        if "sqlite" in str(engine.url):
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

