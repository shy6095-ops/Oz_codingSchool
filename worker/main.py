"""폐렴 예측 AI 워커 (Stage 3 2-2).

흐름:
  1. Redis 작업 큐(List)에서 task 를 꺼낸다 (BLMOVE 로 processing 리스트에 옮겨두어 유실 방지).
  2. worker/model.py 의 ResNet18 모델로 폐렴 예측을 수행한다.
  3. 결과를 job_id 별 Pub/Sub 채널로 발행(PUBLISH)한다. (DB 저장은 FastAPI 담당)
  4. 정상 처리된 task 는 processing 리스트에서 제거한다.

다중 워커: 여러 프로세스/컨테이너가 같은 큐를 BLMOVE 하면 task 가 자동 분배된다.
비정상 종료 복구(선택): 시작 시
  - 이 워커의 processing 리스트는 무조건 큐로 되돌리고,
  - 다른 워커의 processing 리스트는 오래된(STALE_RECLAIM_SECONDS 초과) 작업만 되돌린다.
  두 번째 항목은 컨테이너가 재생성되어 워커 식별자(hostname)가 바뀐 경우의 orphan 을 회수한다.
"""
from __future__ import annotations

import json
import os
import signal
import socket
import sys
import time
from pathlib import Path

import redis
from PIL import Image

from worker.model import MODEL_NAME, predict_pneumonia
from worker.redis_client import TASK_QUEUE, get_redis, result_channel

# 컨테이너에서 media_volume 이 /app/media 로 마운트된다 (docker-compose.yml)
MEDIA_DIR = Path(os.environ.get("MEDIA_DIR", "/app/media/xrays"))

# 워커 식별자: docker-compose --scale 시 컨테이너 hostname 이 replica 별로 고정됨
WORKER_ID = os.environ.get("WORKER_ID") or socket.gethostname()
PROCESSING_QUEUE = f"{TASK_QUEUE}:processing:{WORKER_ID}"

BLOCK_TIMEOUT = 5  # 초. 큐가 비어도 주기적으로 깨어나 종료 신호를 확인
STALE_RECLAIM_SECONDS = 300  # 다른 워커 processing 리스트에서 이 시간 지난 작업은 orphan 으로 보고 회수
_running = True


def _stop(signum, _frame) -> None:
    global _running
    _running = False
    print(f"[worker {WORKER_ID}] signal {signum} 수신 → 종료 준비", flush=True)


def reclaim_pending(r) -> None:
    """시작 시 미완료 task 회수.

    - 내 processing 리스트: 무조건 큐로 되돌린다 (재시작).
    - 다른 워커 processing 리스트: enqueued_at 기준 STALE_RECLAIM_SECONDS 초과분만
      되돌린다 (컨테이너 재생성으로 hostname 이 바뀐 경우의 orphan 회수).
    """
    moved = 0
    # RPOPLPUSH 와 동일: 오른쪽에서 꺼내 큐 왼쪽으로 (재적재분을 먼저 처리)
    while r.lmove(PROCESSING_QUEUE, TASK_QUEUE, "RIGHT", "LEFT"):
        moved += 1

    now = time.time()
    for key in r.scan_iter(match=f"{TASK_QUEUE}:processing:*", count=100):
        if key == PROCESSING_QUEUE:
            continue
        for raw in r.lrange(key, 0, -1):
            try:
                enqueued_at = json.loads(raw).get("enqueued_at", 0)
            except (ValueError, TypeError):
                enqueued_at = 0
            if now - enqueued_at > STALE_RECLAIM_SECONDS:
                if r.lrem(key, 1, raw):
                    r.lpush(TASK_QUEUE, raw)
                    moved += 1

    if moved:
        print(f"[worker {WORKER_ID}] 미완료 task {moved}건 재적재", flush=True)


def run_task(r, raw: str) -> None:
    task = json.loads(raw)
    job_id = task["job_id"]
    channel = result_channel(job_id)
    try:
        image_path = MEDIA_DIR / Path(task["image_name"]).name
        with Image.open(image_path) as image:
            pred = predict_pneumonia(image)
        payload = {
            "job_id": job_id,
            "ok": True,
            "is_pneumonia": pred["is_pneumonia"],
            "confidence": pred["confidence"],
            "ai_model": pred["ai_model"],
        }
        print(
            f"[worker {WORKER_ID}] task {job_id} 완료 "
            f"(record={task.get('record_id')}, is_pneumonia={pred['is_pneumonia']}, "
            f"{pred['confidence']}%)",
            flush=True,
        )
    except Exception as exc:  # noqa: BLE001 - 어떤 실패든 요청자에게 전달
        payload = {"job_id": job_id, "ok": False, "error": f"{type(exc).__name__}: {exc}"}
        print(f"[worker {WORKER_ID}] task {job_id} 실패: {payload['error']}", flush=True)

    r.publish(channel, json.dumps(payload))
    r.lrem(PROCESSING_QUEUE, 1, raw)  # 처리(발행) 완료 → processing 에서 제거


def main() -> int:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    r = get_redis()
    r.ping()
    reclaim_pending(r)
    print(
        f"[worker {WORKER_ID}] 대기 시작 (queue={TASK_QUEUE}, model={MODEL_NAME})",
        flush=True,
    )

    while _running:
        try:
            # 큐(LEFT)에서 꺼내 processing(RIGHT)로 원자적으로 이동 → 처리 중 크래시해도 유실 없음
            raw = r.blmove(TASK_QUEUE, PROCESSING_QUEUE, BLOCK_TIMEOUT, "LEFT", "RIGHT")
        except redis.exceptions.TimeoutError:
            continue  # 큐가 계속 비어있을 때의 소켓 read timeout → 다시 대기
        except redis.exceptions.ConnectionError as exc:
            print(f"[worker {WORKER_ID}] Redis 연결 오류: {exc} → 3초 후 재시도", flush=True)
            time.sleep(3)
            continue
        if raw is None:
            continue
        run_task(r, raw)

    print(f"[worker {WORKER_ID}] 종료", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
