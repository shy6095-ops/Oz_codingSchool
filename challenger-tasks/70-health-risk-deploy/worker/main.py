"""챌린저 70 - 비동기 추론 워커. SIGTERM 을 받으면 진행 중 작업을 마치고 종료한다."""
import json
import os
import signal
import socket
import sys
import time

import redis

sys.path.insert(0, "/app")
from app.predictor import predict  # noqa: E402

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
QUEUE_KEY = "risk:queue"
RESULT_PREFIX = "risk:result:"
RESULT_TTL = int(os.getenv("RESULT_TTL", "900"))

client = redis.from_url(REDIS_URL, decode_responses=True)
WORKER_ID = socket.gethostname()

_shutdown = False


def _on_signal(signum, _frame):
    """
    graceful shutdown.
    docker stop 은 SIGTERM 을 보내고 기본 10초 뒤 SIGKILL 한다.
    플래그만 세우고 루프가 자연히 끝나게 해서 작업이 중간에 끊기지 않게 한다.
    """
    global _shutdown
    _shutdown = True
    print(f"[worker {WORKER_ID}] 종료 신호({signum}) 수신 — 진행 중 작업 후 종료", flush=True)


signal.signal(signal.SIGTERM, _on_signal)
signal.signal(signal.SIGINT, _on_signal)


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
    print(f"[worker {WORKER_ID}] 대기 중", flush=True)

    while not _shutdown:
        item = client.blpop(QUEUE_KEY, timeout=2)
        if item is None:
            continue

        _, raw = item
        try:
            task = json.loads(raw)
            result = predict(task["payload"])
            result["worker"] = WORKER_ID
            client.setex(
                RESULT_PREFIX + task["job_id"], RESULT_TTL, json.dumps(result, ensure_ascii=False)
            )
            print(f"[worker {WORKER_ID}] {task['job_id']} 완료", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[worker {WORKER_ID}] 실패: {exc}", flush=True)

    print(f"[worker {WORKER_ID}] 정상 종료", flush=True)


if __name__ == "__main__":
    main()
