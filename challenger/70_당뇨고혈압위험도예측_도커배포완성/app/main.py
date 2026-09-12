"""
챌린저 70 - Docker를 활용한 웹 서비스 배포 5일차
당뇨 / 고혈압 위험도 예측 서비스 — 배포 완성본

4일차(69) 서비스에 운영 요소를 더했다.
  - Nginx 리버스 프록시 뒤에서 동작
  - Redis 캐시 + 비동기 추론 워커
  - 구조화 로깅 (요청 ID, 처리 시간)
  - IP 기준 요청 제한
  - /healthcheck (liveness) 와 /readyz (readiness) 분리
  - prod 에서 API 문서 비활성화
"""
import json
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, computed_field

from app.config import settings
from app.predictor import load_bundle, predict

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
QUEUE_KEY = "risk:queue"
RESULT_PREFIX = "risk:result:"

redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


# ── 구조화 로깅 ──
class JsonFormatter(logging.Formatter):
    """로그를 JSON 한 줄로 남긴다. 로그 수집기가 바로 파싱할 수 있다."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra_fields"):
            payload.update(record.extra_fields)
        return json.dumps(payload, ensure_ascii=False)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger = logging.getLogger("risk-api")
logger.setLevel(logging.INFO)
logger.handlers = [handler]
logger.propagate = False


@asynccontextmanager
async def lifespan(_: FastAPI):
    bundle = load_bundle()
    logger.info(
        "서비스 기동",
        extra={"extra_fields": {"env": settings.ENV, "model_version": bundle["version"]}},
    )
    yield
    await redis.aclose()
    logger.info("서비스 종료")


# prod 에서는 스키마/문서를 노출하지 않는다.
docs_url = None if settings.is_prod else "/docs"

app = FastAPI(
    title="당뇨 · 고혈압 위험도 예측 서비스",
    version="2.0.0",
    docs_url=docs_url,
    redoc_url=None,
    openapi_url=None if settings.is_prod else "/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def observability(request: Request, call_next):
    """요청 ID 부여 + 처리 시간 기록. Nginx 가 넘긴 ID 를 이어받는다."""
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
    started = time.perf_counter()

    response = await call_next(request)

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-ms"] = str(elapsed_ms)

    # 헬스체크는 로그를 더럽히므로 제외한다.
    if not request.url.path.startswith(("/healthcheck", "/readyz", "/static")):
        logger.info(
            "request",
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "elapsed_ms": elapsed_ms,
                    # Nginx 가 set_real_ip_from 으로 넘긴 실제 클라이언트 IP
                    "client": request.headers.get("X-Forwarded-For", request.client.host if request.client else "?"),
                }
            },
        )
    return response


async def check_rate_limit(request: Request) -> None:
    """
    Redis INCR + EXPIRE 로 분당 요청 수를 센다.
    INCR 은 원자적이라 여러 워커/컨테이너에서 동시에 세도 안전하다.
    """
    client_ip = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    if not client_ip and request.client:
        client_ip = request.client.host

    key = f"ratelimit:{client_ip}:{int(time.time() // 60)}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 70)  # 분 경계를 넘겨 조금 여유를 둔다

    if count > settings.RATE_LIMIT_PER_MIN:
        raise HTTPException(
            status_code=429,
            detail=f"요청이 너무 많습니다. 분당 {settings.RATE_LIMIT_PER_MIN}회까지 가능합니다.",
        )


class RiskRequest(BaseModel):
    age: int = Field(..., ge=19, le=100)
    height_cm: float = Field(..., ge=120, le=220)
    weight_kg: float = Field(..., ge=30, le=200)
    systolic: float = Field(..., ge=70, le=250)
    diastolic: float = Field(..., ge=40, le=150)
    glucose: float = Field(..., ge=40, le=500)
    hba1c: float = Field(..., ge=3.0, le=15.0)
    family_history: int = Field(0, ge=0, le=1)
    smoker: int = Field(0, ge=0, le=1)
    exercise_days: int = Field(0, ge=0, le=7)

    @computed_field
    @property
    def bmi(self) -> float:
        return round(self.weight_kg / ((self.height_cm / 100) ** 2), 2)


def cache_key(body: dict) -> str:
    import hashlib

    raw = json.dumps(body, sort_keys=True)
    return "risk:cache:" + hashlib.sha256(raw.encode()).hexdigest()[:24]


# ── 헬스 엔드포인트 (liveness / readiness 분리) ──
@app.get("/healthcheck")
async def healthcheck():
    """liveness: 프로세스가 살아있는가. 의존성을 확인하지 않는다."""
    return {"status": "ok", "env": settings.ENV}


@app.get("/readyz")
async def readyz():
    """readiness: 트래픽을 받을 준비가 됐는가. 모델과 Redis 를 확인한다."""
    checks = {}
    try:
        checks["model"] = load_bundle()["version"]
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(status_code=503, content={"status": "not-ready", "model": str(exc)})

    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(status_code=503, content={"status": "not-ready", "redis": str(exc)})

    return {"status": "ready", **checks}


@app.get("/api/model")
async def model_info():
    bundle = load_bundle()
    return {
        "version": bundle["version"],
        "targets": {k: {"label": v["label"], "metrics": v["metrics"]} for k, v in bundle["targets"].items()},
    }


@app.post("/api/predict")
async def predict_risk(payload: RiskRequest, request: Request):
    await check_rate_limit(request)

    body = payload.model_dump()
    key = cache_key(body)

    cached = await redis.get(key)
    if cached:
        return {**json.loads(cached), "cached": True}

    result = predict(body)
    result["input"] = {"bmi": body["bmi"]}
    await redis.setex(key, settings.CACHE_TTL, json.dumps(result, ensure_ascii=False))
    return {**result, "cached": False}


@app.post("/api/predict/async")
async def predict_async(payload: RiskRequest, request: Request):
    """대량 배치·무거운 모델을 대비한 비동기 경로."""
    await check_rate_limit(request)

    body = payload.model_dump()
    job_id = uuid.uuid4().hex[:16]
    await redis.rpush(QUEUE_KEY, json.dumps({"job_id": job_id, "payload": body}))
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/predict/result/{job_id}")
async def predict_result(job_id: str):
    raw = await redis.get(RESULT_PREFIX + job_id)
    if raw is None:
        return {"job_id": job_id, "status": "pending", "queue_length": await redis.llen(QUEUE_KEY)}
    return {"job_id": job_id, "status": "done", **json.loads(raw)}


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
