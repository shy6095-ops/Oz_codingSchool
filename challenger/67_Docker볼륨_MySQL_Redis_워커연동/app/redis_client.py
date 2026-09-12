"""Redis 연결과 분산 락."""
import asyncio
import time
import uuid
from contextlib import asynccontextmanager

import redis.asyncio as aioredis

from app.config import settings

redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

QUEUE_KEY = "reservation:queue"

# 락을 건 주인만 락을 풀도록 보장하는 Lua 스크립트.
# GET 후 DEL 을 따로 하면 그 사이에 락이 만료되고 남이 잡을 수 있다. (원자성 필요)
_UNLOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


@asynccontextmanager
async def distributed_lock(key: str, ttl: int = 5, wait: float = 3.0):
    """
    Redis 분산 락. SET NX EX 로 "없을 때만 쓰기 + 만료시간" 을 한 번에 처리한다.

    - NX : 키가 없을 때만 성공 -> 먼저 잡은 하나만 통과
    - EX : 만료시간. 락 잡은 프로세스가 죽어도 자동 해제되어 데드락을 막는다
    - token : 내가 건 락인지 식별. 남의 락을 풀지 않기 위해 필요
    """
    token = uuid.uuid4().hex
    deadline = time.monotonic() + wait

    while True:
        acquired = await redis.set(key, token, nx=True, ex=ttl)
        if acquired:
            break
        if time.monotonic() >= deadline:
            raise TimeoutError(f"락 획득 실패: {key}")
        await asyncio.sleep(0.01)

    try:
        yield
    finally:
        await redis.eval(_UNLOCK_SCRIPT, 1, key, token)
