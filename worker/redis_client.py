"""AI 워커용 Redis 동기 클라이언트 (Stage 3 2-1).

- 작업 큐(List)에서 task 를 꺼내고(BLMOVE)
- 결과 채널(Pub/Sub)로 예측 결과를 발행(PUBLISH)한다.

큐/채널 이름은 FastAPI 쪽(app/core/redis_client.py)과 반드시 일치해야 한다.
"""
from __future__ import annotations

import os

import redis

# --- FastAPI <-> Worker 간 Redis 규약 (app/core/redis_client.py 와 동일) --------
TASK_QUEUE = "pneumonia:tasks"
RESULT_CHANNEL_PREFIX = "pneumonia:results:"


def result_channel(job_id: str) -> str:
    return f"{RESULT_CHANNEL_PREFIX}{job_id}"


# 로컬 실행은 localhost, docker-compose 에서는 REDIS_URL 환경변수로 redis 서비스명을 주입
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


# BLMOVE/BLPOP 등 블로킹 명령의 서버측 timeout 보다 소켓 read timeout 이 커야
# "Timeout reading from socket" 로 죽지 않는다 (BLOCK_TIMEOUT + 여유).
SOCKET_TIMEOUT = 30


def get_redis() -> "redis.Redis":
    return redis.Redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_timeout=SOCKET_TIMEOUT,
        socket_keepalive=True,
        health_check_interval=30,
    )
