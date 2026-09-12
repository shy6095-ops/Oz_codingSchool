"""
챌린저 68 - Docker를 활용한 웹 서비스 배포 3일차

FastAPI + Redis 로 모델을 서빙한다. 두 가지 경로를 제공한다.

  POST /predict        동기 추론 + Redis 캐시 (같은 입력이면 즉시 응답)
  POST /predict/async  Redis 큐에 적재 -> 워커가 추론 -> 결과 조회
"""
import hashlib
import json
import os
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.model import load_model, predict

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))
QUEUE_KEY = "predict:queue"
RESULT_PREFIX = "predict:result:"

redis = aioredis.from_url(REDIS_URL, decode_responses=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 기동 시 모델을 미리 읽어둔다. 첫 요청이 느려지는 것(cold start)을 막는다.
    model = load_model()
    print(f"[api] 모델 로드 완료 v{model['version']} · {model['metrics']}", flush=True)
    yield
    await redis.aclose()


app = FastAPI(
    title="Docker 3일차 - 대사증후군 위험도 모델 서빙",
    description="FastAPI + Redis 캐시 + 비동기 워커 추론",
    version="1.0.0",
    lifespan=lifespan,
)


class PredictRequest(BaseModel):
    bmi: float = Field(..., ge=10, le=60, examples=[23.2])
    systolic: float = Field(..., ge=70, le=250, description="수축기 혈압 mmHg", examples=[128])
    glucose: float = Field(..., ge=40, le=500, description="공복 혈당 mg/dL", examples=[104])
    age: int = Field(..., ge=0, le=120, examples=[44])
    smoker: int = Field(0, ge=0, le=1, description="흡연 여부 0/1", examples=[0])


def cache_key(payload: dict) -> str:
    """입력을 정렬 직렬화해서 해시. 키 순서가 달라도 같은 캐시를 맞춘다."""
    raw = json.dumps(payload, sort_keys=True)
    return "predict:cache:" + hashlib.sha256(raw.encode()).hexdigest()[:24]


@app.get("/healthcheck")
async def healthcheck():
    await redis.ping()
    return {"status": "ok", "model_version": load_model()["version"]}


@app.get("/model")
async def model_info():
    """서빙 중인 모델의 버전·계수·성능을 확인한다."""
    return load_model()


@app.post("/predict")
async def predict_sync(payload: PredictRequest):
    body = payload.model_dump()
    key = cache_key(body)

    cached = await redis.get(key)
    if cached:
        return {**json.loads(cached), "cached": True}

    result = predict(body)
    await redis.setex(key, CACHE_TTL, json.dumps(result, ensure_ascii=False))
    return {**result, "cached": False}


@app.post("/predict/async")
async def predict_async(payload: PredictRequest):
    """
    추론을 워커에게 넘기고 job_id 만 돌려준다.
    모델이 무거워질수록(딥러닝 등) 이 구조가 필요하다.
    """
    body = payload.model_dump()
    job_id = hashlib.sha256(
        (json.dumps(body, sort_keys=True) + os.urandom(8).hex()).encode()
    ).hexdigest()[:16]

    await redis.rpush(QUEUE_KEY, json.dumps({"job_id": job_id, "payload": body}))
    return {"job_id": job_id, "status": "queued"}


@app.get("/predict/result/{job_id}")
async def predict_result(job_id: str):
    raw = await redis.get(RESULT_PREFIX + job_id)
    if raw is None:
        queued = await redis.llen(QUEUE_KEY)
        return {"job_id": job_id, "status": "pending", "queue_length": queued}
    return {"job_id": job_id, "status": "done", **json.loads(raw)}


@app.get("/cache/stats")
async def cache_stats():
    """캐시 적중 효과를 눈으로 확인하기 위한 보조 엔드포인트."""
    keys = [k async for k in redis.scan_iter("predict:cache:*")]
    info = await redis.info("stats")
    hits = int(info.get("keyspace_hits", 0))
    misses = int(info.get("keyspace_misses", 0))
    total = hits + misses
    return {
        "cached_entries": len(keys),
        "keyspace_hits": hits,
        "keyspace_misses": misses,
        "hit_rate": round(hits / total, 4) if total else None,
        "ttl_seconds": CACHE_TTL,
    }
