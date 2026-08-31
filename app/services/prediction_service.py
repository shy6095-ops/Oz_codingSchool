from decimal import Decimal
from pathlib import Path

from fastapi import HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.models.ai_analysis_result import AiAnalysisResult
from app.repositories.prediction_repository import PredictionRepository
from worker.model import predict


AI_MODEL_NAME = "SimpleCNN"
MEDIA_DIR = Path(__file__).resolve().parents[2] / "media"


class PredictionService:
    def __init__(self, repository: PredictionRepository):
        self.repository = repository

    async def predict_for_record(self, record_id: int) -> AiAnalysisResult:
        existing_result = await self.repository.get_result_by_model(
            record_id=record_id, ai_model=AI_MODEL_NAME
        )
        if existing_result:
            return existing_result

        record = await self.repository.get_record_with_images(record_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="진료 기록을 찾을 수 없습니다.",
            )
        if not record.xray_images:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="예측에 사용할 X-ray 이미지가 없습니다.",
            )

        image_url = record.xray_images[0].image_url
        image_path = (MEDIA_DIR / image_url.removeprefix("/media/")).resolve()
        if not image_path.is_relative_to(MEDIA_DIR.resolve()) or not image_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="저장된 X-ray 이미지 파일을 찾을 수 없습니다.",
            )

        # PyTorch inference is CPU-bound, so it runs outside FastAPI's event loop.
        prediction = await run_in_threadpool(predict, image_path)
        return await self.repository.create_result(
            record_id=record_id,
            is_pneumonia=bool(prediction["is_pneumonia"]),
            confidence=Decimal(str(prediction["confidence"])),
            ai_model=AI_MODEL_NAME,
        )

    async def get_result_list(self, record_id: int) -> list[AiAnalysisResult]:
        record = await self.repository.get_record_with_images(record_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="진료 기록을 찾을 수 없습니다.",
            )
        return await self.repository.get_result_list(record_id)
