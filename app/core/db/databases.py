from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATABASE_PATH = PROJECT_ROOT / "db" / "ai_health.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"

# 비동기 엔진 생성
async_engine = create_async_engine(DATABASE_URL, echo=False, future=True)
# 비동기 세션 팩토리 생성
AsyncSessionLocal = async_sessionmaker(bind=async_engine, autoflush=False, expire_on_commit=False)
# 모델 베이스 생성
Base = declarative_base()

async def async_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as db:
        yield db


async def init_db() -> None:
    """로컬 SQLite 파일과 과제에 필요한 테이블을 준비한다."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    # 모든 모델을 등록한 뒤 metadata를 생성한다.
    from app import models  # noqa: F401

    async with async_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
