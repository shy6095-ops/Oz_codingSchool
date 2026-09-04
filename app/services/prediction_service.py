"""폐렴 예측 서비스 (Stage 3 1-2).

기존에는 FastAPI 프로세스 안에서 직접 추론했지만, 이제는
  1. (record_id, ai_model) 로 DB 캐시를 먼저 확인하고 (필수)
  2. 없으면 Redis 작업 큐에 task 를 등록한 뒤 결과 채널을 구독해
  3. AI 워커가 발행한 결과를 받아 DB 에 저장하고 응답한다.
"""
from __future__ import annotations

import asyncio
import json
import time
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.redis_client import TASK_QUEUE, get_redis, result_channel
from app.models.ai_analysis_result import AiAnalysisResult
from app.models.medical_record import MedicalRecord
from app.schemas.prediction import PredictionResponse

# 워커가 결과를 발행하기까지 기다리는 최대 시간(초). 첫 요청은 워커의 모델 로드가 포함될 수 있어 넉넉히 둔다.
RESULT_TIMEOUT_SECONDS = 60
# 동시 요청(따닥) 방지용 in-flight 락 TTL(초)
INFLIGHT_TTL_SECONDS = RESULT_TIMEOUT_SECONDS + 10


def _prediction_response(result: AiAnalysisResult) -> PredictionResponse:
    return PredictionResponse.model_validate(result)


class PredictionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_record_with_xray(self, record_id: int) -> MedicalRecord:
        record = await self.session.scalar(
            select(MedicalRecord)
            .options(selectinload(MedicalRecord.xray_images))
            .where(MedicalRecord.id == record_id)
        )
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="진료 기록을 찾을 수 없습니다."
            )
        return record

    async def _get_cached_result(self, record_id: int) -> AiAnalysisResult | None:
        return await self.session.scalar(
            select(AiAnalysisResult).where(
                AiAnalysisResult.record_id == record_id,
                AiAnalysisResult.ai_model == settings.AI_MODEL_NAME,
            )
        )

    async def predict(self, record_id: int) -> tuple[PredictionResponse, bool]:
        """같은 모델로 저장된 결과가 있으면 재사용, 없으면 워커에 추론을 위임한다.
        반환 bool: 새로 추론했으면 True, 캐시 반환이면 False.
        """
        record = await self._get_record_with_xray(record_id)

        cached = await self._get_cached_result(record_id)
        if cached is not None:
            return _prediction_response(cached), False

        if not record.xray_images:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="해당 진료기록에 연결된 X-Ray 이미지가 없습니다.",
            )

        image_name = Path(record.xray_images[-1].image_url).name
        prediction = await self._run_via_worker(record_id, image_name)

        # 동시 첫 요청 중 다른 요청이 먼저 저장했을 수 있으니 재확인해 중복 row 를 막는다.
        # (완전 차단은 (record_id, ai_model) unique 제약이 필요하지만, 여기서 대부분의
        #  동시 케이스는 걸러진다. 따닥 락으로 중복 '추론' 은 이미 방지됨.)
        cached = await self._get_cached_result(record_id)
        if cached is not None:
            return _prediction_response(cached), False

        result = AiAnalysisResult(
            record_id=record_id,
            is_pneumonia=prediction["is_pneumonia"],
            confidence=Decimal(str(prediction["confidence"])),
            heatmap_url=None,
            ai_model=prediction["ai_model"],
        )
        self.session.add(result)
        await self.session.commit()
        await self.session.refresh(result)
        return _prediction_response(result), True

    async def _run_via_worker(self, record_id: int, image_name: str) -> dict:
        """Redis 작업 큐에 task 를 넣고 워커가 Pub/Sub 으로 발행한 결과를 기다린다."""
        redis = get_redis()

        # 따닥 방지: 같은 (record_id, model) 요청이 이미 진행 중이면 그 job 의 결과를 같이 구독한다.
        inflight_key = f"pneumonia:inflight:{record_id}:{settings.AI_MODEL_NAME}"
        job_id = uuid4().hex
        owns_job = await redis.set(inflight_key, job_id, nx=True, ex=INFLIGHT_TTL_SECONDS)
        if not owns_job:
            job_id = await redis.get(inflight_key)
            if job_id is None:  # 방금 만료됨 → 우리가 새로 맡는다
                job_id = uuid4().hex
                await redis.set(inflight_key, job_id, ex=INFLIGHT_TTL_SECONDS)
                owns_job = True

        channel = result_channel(job_id)
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)  # RPUSH 전에 먼저 구독해야 결과 유실이 없다
        try:
            if owns_job:
                task = {
                    "job_id": job_id,
                    "record_id": record_id,
                    "image_name": image_name,
                    "enqueued_at": time.time(),  # 워커의 stale 작업 회수 판단용
                }
                await redis.rpush(TASK_QUEUE, json.dumps(task))

            payload = await self._wait_for_result(pubsub)
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
            if owns_job:
                await redis.delete(inflight_key)

        if not payload.get("ok"):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI 워커 추론 실패: {payload.get('error', 'unknown')}",
            )
        return payload

    @staticmethod
    async def _wait_for_result(pubsub) -> dict:
        try:
            async with asyncio.timeout(RESULT_TIMEOUT_SECONDS):
                while True:
                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )
                    if message and message.get("type") == "message":
                        return json.loads(message["data"])
        except TimeoutError:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="AI 워커 응답 시간 초과",
            )

    async def list_predictions(self, record_id: int) -> list[PredictionResponse]:
        await self._get_record_with_xray(record_id)
        results = (
            await self.session.scalars(
                select(AiAnalysisResult)
                .where(AiAnalysisResult.record_id == record_id)
                .order_by(AiAnalysisResult.id.desc())
            )
        ).all()
        return [_prediction_response(result) for result in results]
