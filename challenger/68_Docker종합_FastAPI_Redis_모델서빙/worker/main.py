"""
챌린저 68 - 추론 워커

Redis 큐에서 작업을 꺼내 추론하고 결과를 다시 Redis 에 저장한다.
api 와 같은 model.py 를 쓰지만 별도 이미지/컨테이너로 뜬다.
"""
import json
import os
import socket
import time

import redis

from app.model import predict

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
QUEUE_KEY = "predict:queue"
RESULT_PREFIX = "predict:result:"
RESULT_TTL = int(os.getenv("RESULT_TTL", "600"))

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


def main() -> None:
    wait_for_redis()
    print(f"[worker {WORKER_ID}] 추론 대기 중...", flush=True)

    while True:
        item = client.blpop(QUEUE_KEY, timeout=5)
        if item is None:
            continue

        _, raw = item
        try:
            task = json.loads(raw)
            result = predict(task["payload"])
            result["worker"] = WORKER_ID
        except Exception as exc:  # noqa: BLE001
            print(f"[worker {WORKER_ID}] 실패: {exc}", flush=True)
            continue

        client.setex(
            RESULT_PREFIX + task["job_id"], RESULT_TTL, json.dumps(result, ensure_ascii=False)
        )
        print(
            f"[worker {WORKER_ID}] {task['job_id']} -> "
            f"{result['probability']} ({result['risk']})",
            flush=True,
        )


if __name__ == "__main__":
    main()
