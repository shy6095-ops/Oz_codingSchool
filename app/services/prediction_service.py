import asyncio
from decimal import Decimal
from pathlib import Path

from fastapi import HTTPException, status
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai_analysis_result import AiAnalysisResult
from app.models.medical_record import MedicalRecord
from app.schemas.prediction import PredictionResponse
from worker.model import MODEL_NAME, predict_pneumonia

MEDIA_DIR = Path(__file__).resolve().parents[2] / "media" / "xrays"


def _prediction_response(result: AiAnalysisResult) -> PredictionResponse:
    return PredictionResponse.model_validate(result)


def _run_inference(image_path: Path) -> dict:
    with Image.open(image_path) as image:
        return predict_pneumonia(image)


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
                AiAnalysisResult.ai_model == MODEL_NAME,
            )
        )

    async def predict(self, record_id: int) -> tuple[PredictionResponse, bool]:
        """REQ-PRED-001: 같은 모델로 저장된 결과가 있으면 재사용하고, 없으면 새로 추론한다.
        반환값의 bool은 새로 추론했는지(True) 캐시를 반환했는지(False)를 나타낸다.
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

        latest_image = record.xray_images[-1]
        image_path = MEDIA_DIR / Path(latest_image.image_url).name
        prediction = await asyncio.to_thread(_run_inference, image_path)

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
