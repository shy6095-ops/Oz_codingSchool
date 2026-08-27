from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from typing import AsyncGenerator
from app.core.config import settings


DATABASE_PREFIX = "mysql+asyncmy://"
DATABASE_URI = f"{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
DATABASE_URL = settings.DATABASE_URL or f"{DATABASE_PREFIX}{DATABASE_URI}"

# 비동기 엔진 생성
engine_options = {"echo": False, "future": True}
if DATABASE_URL.startswith("sqlite+aiosqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
async_engine = create_async_engine(DATABASE_URL, **engine_options)
# 비동기 세션 팩토리 생성
AsyncSessionLocal = async_sessionmaker(bind=async_engine, autoflush=False, expire_on_commit=False)
# 모델 베이스 생성
Base = declarative_base()

# 세션 생성 함수
async def async_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as db:
        yield db
