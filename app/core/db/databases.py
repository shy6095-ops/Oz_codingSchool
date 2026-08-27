from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL

if DATABASE_URL.startswith("sqlite"):
    Path("db").mkdir(exist_ok=True)
    engine_options = {"connect_args": {"check_same_thread": False}}
else:
    engine_options = {}

async_engine = create_async_engine(DATABASE_URL, echo=False, future=True, **engine_options)
AsyncSessionLocal = async_sessionmaker(bind=async_engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


@event.listens_for(async_engine.sync_engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async def initialize_database() -> None:
    """Create local SQLite tables and enable SQLite's durable write mode."""
    import app.models  # noqa: F401 - import models before evaluating metadata

    async with async_engine.begin() as connection:
        if DATABASE_URL.startswith("sqlite"):
            await connection.execute(text("PRAGMA journal_mode=WAL"))
        await connection.run_sync(Base.metadata.create_all)

# 세션 생성 함수
async def async_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as db:
        yield db
