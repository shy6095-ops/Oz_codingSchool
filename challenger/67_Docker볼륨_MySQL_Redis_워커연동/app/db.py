"""비동기 DB 엔진/세션. MySQL 컨테이너가 늦게 뜨는 경우를 대비해 재시도한다."""
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models import Base

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,   # 끊긴 커넥션을 재사용하지 않도록 먼저 확인
    pool_recycle=280,
)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


async def init_db(retries: int = 15, delay: float = 2.0) -> None:
    """
    테이블을 만든다.
    compose 의 depends_on + healthcheck 를 걸어도 MySQL 초기화가 더 걸릴 수 있어서
    애플리케이션 쪽에서도 재시도를 둔다. (실전에서 꼭 필요한 방어 코드)
    """
    for attempt in range(1, retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            return
        except Exception as exc:  # noqa: BLE001
            if attempt == retries:
                raise
            print(f"[init_db] MySQL 연결 대기 {attempt}/{retries}: {exc}")
            await asyncio.sleep(delay)
