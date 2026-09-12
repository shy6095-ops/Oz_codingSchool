"""
챌린저 67 - 예약 확정 알림 워커

FastAPI 가 Redis 큐(reservation:queue)에 넣은 작업을 꺼내 처리한다.
- BLPOP 으로 블로킹 대기 -> 폴링 없이 즉시 처리
- 컨테이너를 여러 개 띄우면(--scale) 각 작업이 한 번씩만 분배된다
"""
import json
import os
import socket
import time

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
QUEUE_KEY = "reservation:queue"
DONE_KEY = "reservation:done"

client = redis.from_url(REDIS_URL, decode_responses=True)
WORKER_ID = socket.gethostname()


def wait_for_redis(retries: int = 30, delay: float = 1.0) -> None:
    for attempt in range(1, retries + 1):
        try:
            client.ping()
            return
        except redis.ConnectionError as exc:
            if attempt == retries:
                raise
            print(f"[worker {WORKER_ID}] Redis 대기 {attempt}/{retries}: {exc}", flush=True)
            time.sleep(delay)


def handle(task: dict) -> dict:
    """실제 알림 발송 자리. 여기서는 처리 흔적만 남긴다."""
    time.sleep(0.2)  # 외부 API 호출을 흉내
    return {
        "reservation_id": task["reservation_id"],
        "patient_name": task["patient_name"],
        "message": f"{task['patient_name']}님 예약이 확정되었습니다.",
        "worker": WORKER_ID,
    }


def main() -> None:
    wait_for_redis()
    print(f"[worker {WORKER_ID}] 시작. 큐 대기 중...", flush=True)

    while True:
        # BLPOP: 큐가 빌 때까지 블로킹. timeout 을 두어 종료 신호를 받을 수 있게 한다.
        item = client.blpop(QUEUE_KEY, timeout=5)
        if item is None:
            continue

        _, raw = item
        try:
            task = json.loads(raw)
        except json.JSONDecodeError:
            print(f"[worker {WORKER_ID}] 잘못된 작업 무시: {raw}", flush=True)
            continue

        result = handle(task)
        client.rpush(DONE_KEY, json.dumps(result, ensure_ascii=False))
        print(f"[worker {WORKER_ID}] 처리 완료: {result['message']}", flush=True)


if __name__ == "__main__":
    main()
