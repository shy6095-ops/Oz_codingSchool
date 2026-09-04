"""FastAPI 앱용 Redis 비동기 클라이언트 (Stage 3 1-1).

- 작업 큐(List)에 폐렴 예측 task 를 넣고(RPUSH)
- 결과 채널(Pub/Sub)을 구독해 워커가 발행한 결과를 받는다.

큐/채널 이름은 worker 쪽(worker/redis_client.py)과 반드시 일치해야 한다.
"""
from __future__ import annotations

from redis.asyncio import Redis

from app.core.config import settings

# --- FastAPI <-> Worker 간 Redis 규약 ------------------------------------------
TASK_QUEUE = "pneumonia:tasks"                       # List: RPUSH(app) / BLMOVE(worker)
RESULT_CHANNEL_PREFIX = "pneumonia:results:"          # Pub/Sub: job_id 별 결과 채널


def result_channel(job_id: str) -> str:
    return f"{RESULT_CHANNEL_PREFIX}{job_id}"


# --- 커넥션 (앱 프로세스당 1개, 커넥션 풀은 redis-py 가 내부 관리) ----------------
_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
